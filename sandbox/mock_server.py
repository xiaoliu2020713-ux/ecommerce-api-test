"""Fake Store API 本地 Mock 服务（零第三方依赖，仅用标准库）。

为什么需要它？
    GitHub Actions 等云 CI 运行在数据中心 IP 上，访问公开的 ``https://fakestoreapi.com``
    会被 Cloudflare 的机器人防护拦截，返回 ``403`` 与 "Just a moment..." 挑战页。
    为了让 CI 能稳定执行同一套用例，这里用标准库复刻了被测接口的行为契约。

关键契约（与线上保持一致）：
    * ``POST /auth/login``    账号 ``mor_2314 / 83r5^_`` 返回 ``201`` + ``{"token": ...}``；
                              其它账号返回 ``401``。
    * ``GET  /products``      返回 20 个商品。
    * ``GET  /products/{id}`` 不存在时返回 ``200`` + 空响应体（不是 404，与线上一致）。
    * ``GET  /carts/{id}``    不存在时返回 ``200`` + ``null``（与线上一致）。
    * ``POST /carts``         返回 ``201`` + 新建购物车（不回写数据，与线上一致）。
    * ``GET  /carts/user/{id}`` 返回该用户的购物车列表。

用法::

    python mock_server.py --port 8765         # 命令行启动
    from mock_server import start_mock_server # 在代码中启动
"""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple
from urllib.parse import unquote, urlparse

# --------------------------------------------------------------------------- #
# 测试数据（结构与线上一致，规模收敛以便维护）
# --------------------------------------------------------------------------- #
VALID_USERNAME = "mor_2314"
VALID_PASSWORD = "83r5^_"

CATEGORIES = ["electronics", "jewelery", "men's clothing", "women's clothing"]

#: 20 个商品，覆盖全部分类，字段与线上一致
PRODUCTS: List[Dict[str, Any]] = []
for _index in range(1, 21):
    _category = CATEGORIES[(_index - 1) % len(CATEGORIES)]
    PRODUCTS.append(
        {
            "id": _index,
            "title": f"Mock Product {_index} ({_category})",
            "price": round(10.0 + _index * 5.5, 2),
            "description": f"这是第 {_index} 个用于接口测试的模拟商品。",
            "category": _category,
            "image": f"https://fakestoreapi.com/img/mock-product-{_index}.jpg",
            "rating": {"rate": 4.0, "count": 100 + _index},
        }
    )

#: 用户数据，字段与线上一致
USERS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "email": "john@gmail.com",
        "username": "johnd",
        "password": "m38rmF$",
        "name": {"firstname": "john", "lastname": "doe"},
        "address": {
            "geolocation": {"lat": "-37.3159", "long": "81.1496"},
            "city": "kilcoole",
            "street": "new road",
            "number": 7682,
            "zipcode": "12926-3874",
        },
        "phone": "1-570-236-7033",
    },
    {
        "id": 2,
        "email": "morrison@gmail.com",
        "username": "mor_2314",
        "password": "83r5^_",
        "name": {"firstname": "david", "lastname": "morrison"},
        "address": {
            "geolocation": {"lat": "29.4572", "long": "-164.2990"},
            "city": "Gotham",
            "street": "Gotham Street",
            "number": 1234,
            "zipcode": "12926-3874",
        },
        "phone": "1-570-236-7033",
    },
]

#: 购物车数据，全部属于 userId=1
CARTS: List[Dict[str, Any]] = [
    {
        "id": _cart_id,
        "userId": 1,
        "date": f"2020-0{_cart_id}-02T00:00:00.000Z",
        "products": [
            {"productId": _cart_id, "quantity": _cart_id},
            {"productId": _cart_id + 1, "quantity": 1},
        ],
    }
    for _cart_id in range(1, 8)
]

#: 下一个可用的购物车 ID
_NEXT_CART_ID = len(CARTS) + 1

#: 模拟 token（结构上是一个三段式 JWT，满足用例的格式校验）
MOCK_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOjIsInVzZXIiOiJtb3JfMjMxNCIsImlhdCI6MTcwMDAwMDAwMH0."
    "bW9jay1zaWduYXR1cmUtZm9yLWxvY2FsLXRlc3Q"
)


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #
def _route(method: str, path: str, body: Any) -> Tuple[int, Any, bool]:
    """根据请求返回 ``(状态码, 响应体, 是否返回 JSON)``。"""
    global _NEXT_CART_ID

    # ---------------- 登录 ----------------
    if method == "POST" and path == "/auth/login":
        payload = body if isinstance(body, dict) else {}
        if (
            payload.get("username") == VALID_USERNAME
            and payload.get("password") == VALID_PASSWORD
        ):
            return 201, {"token": MOCK_TOKEN}, True
        return 401, "username or password is incorrect", False

    # ---------------- 商品 ----------------
    if method == "GET" and path == "/products":
        return 200, PRODUCTS, True

    if method == "GET" and path == "/products/categories":
        return 200, CATEGORIES, True

    if method == "GET" and path.startswith("/products/category/"):
        category = unquote(path[len("/products/category/"):])
        matched = [item for item in PRODUCTS if item["category"] == category]
        return 200, matched, True

    if method == "GET" and path.startswith("/products/"):
        raw_id = path[len("/products/"):]
        if raw_id.isdigit():
            matched = [item for item in PRODUCTS if item["id"] == int(raw_id)]
            if matched:
                return 200, matched[0], True
            # 线上行为：不存在的商品返回 200 + 空响应体
            return 200, None, False
        return 200, None, False

    # ---------------- 用户 ----------------
    if method == "GET" and path == "/users":
        return 200, USERS, True

    if method == "GET" and path.startswith("/users/"):
        raw_id = path[len("/users/"):]
        if raw_id.isdigit():
            matched = [item for item in USERS if item["id"] == int(raw_id)]
            if matched:
                return 200, matched[0], True
        return 200, None, True

    # ---------------- 购物车 ----------------
    if method == "POST" and path == "/carts":
        payload = body if isinstance(body, dict) else {}
        new_cart = {
            "id": _NEXT_CART_ID,
            "userId": payload.get("userId"),
            "date": payload.get("date")
            or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "products": payload.get("products", []),
        }
        _NEXT_CART_ID += 1
        return 201, new_cart, True

    if method == "GET" and path == "/carts":
        return 200, CARTS, True

    if method == "GET" and path.startswith("/carts/user/"):
        raw_id = path[len("/carts/user/"):]
        if raw_id.isdigit():
            matched = [c for c in CARTS if c["userId"] == int(raw_id)]
            return 200, matched, True
        return 200, [], True

    if method == "GET" and path.startswith("/carts/"):
        raw_id = path[len("/carts/"):]
        if raw_id.isdigit():
            matched = [c for c in CARTS if c["id"] == int(raw_id)]
            if matched:
                return 200, matched[0], True
        # 线上行为：不存在的购物车返回 200 + null
        return 200, None, True

    return 404, {"error": f"no route for {method} {path}"}, True


# --------------------------------------------------------------------------- #
# HTTP 处理
# --------------------------------------------------------------------------- #
class MockHandler(BaseHTTPRequestHandler):
    """把请求转交给 :func:`_route` 并返回结果。"""

    server_version = "FakeStoreMock/1.0"

    def _handle(self, method: str) -> None:  # noqa: D102
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        body: Any = None
        length = int(self.headers.get("Content-Length") or 0)
        if length > 0:
            raw = self.rfile.read(length)
            try:
                body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                body = None

        status, payload, as_json = _route(method, path, body)

        if payload is None and as_json:
            data = b"null"
        elif as_json:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        elif payload is None:
            data = b""
        else:
            data = str(payload).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._handle("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._handle("DELETE")

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D102
        # 静默处理，避免污染 pytest 输出
        return


# --------------------------------------------------------------------------- #
# 启停入口
# --------------------------------------------------------------------------- #
def start_mock_server(port: int = 0, host: str = "127.0.0.1") -> Tuple[ThreadingHTTPServer, str]:
    """启动 Mock 服务（后台线程），返回 ``(server, base_url)``。

    Args:
        port: 端口，``0`` 表示由系统分配一个空闲端口。
        host: 监听地址。
    """
    server = ThreadingHTTPServer((host, port), MockHandler)
    thread = threading.Thread(target=server.serve_forever, name="mock-fakestore", daemon=True)
    thread.start()
    actual_port = server.server_address[1]
    return server, f"http://{host}:{actual_port}"


def main() -> None:
    """命令行入口：``python mock_server.py --port 8765``。"""
    parser = argparse.ArgumentParser(description="Fake Store API 本地 Mock 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8765, help="监听端口（默认 8765）")
    args = parser.parse_args()

    server, base_url = start_mock_server(port=args.port, host=args.host)
    print(f"Mock Fake Store API 已启动：{base_url}")
    print("可用接口：POST /auth/login, GET /products, GET /products/{id}, "
          "GET /products/category/{category}, GET /users/{id}, GET /carts/{id}, POST /carts")
    print("按 Ctrl+C 停止。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止 Mock 服务 ...")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
