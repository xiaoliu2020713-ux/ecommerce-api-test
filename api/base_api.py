"""基础接口封装模块。

本模块提供 :class:`BaseAPI` ，对 ``requests.Session`` 做统一封装，
统一处理 base_url、公共请求头、日志、Allure 步骤记录与响应附件。
所有业务 API 类（用户、商品、购物车）都继承自该类。
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import allure
import requests

LOGGER = logging.getLogger("ecommerce_api_test")

#: 被测试系统的默认地址（公开的 Fake Store API）
DEFAULT_BASE_URL = "https://fakestoreapi.com"

#: 默认请求头
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "ecommerce-api-test/1.0 (+pytest+requests)",
}

#: 附件体积上限（字符数），避免超长响应撑爆报告
MAX_ATTACHMENT_CHARS = 20000

#: 打印或写入附件时需要脱敏的字段
SENSITIVE_FIELDS = ("password", "token", "authorization", "access_token")


def _sanitize(payload: Any) -> Any:
    """对请求数据做浅层脱敏，避免密码 / token 泄漏到日志和 Allure 报告中。"""
    if isinstance(payload, dict):
        sanitized: Dict[str, Any] = {}
        for key, value in payload.items():
            if str(key).lower() in SENSITIVE_FIELDS:
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    return payload


def _to_pretty_json(value: Any) -> str:
    """把任意对象转换成便于阅读的 JSON 文本。"""
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except (TypeError, ValueError):
        return str(value)


def _truncate(text: str) -> str:
    if len(text) <= MAX_ATTACHMENT_CHARS:
        return text
    return text[:MAX_ATTACHMENT_CHARS] + "\n... (内容过长，已截断)"


class BaseAPI:
    """所有业务接口类的基类。

    功能：
        1. 复用 ``requests.Session``（连接池 + 会话级公共头），提升执行效率；
        2. 拼接 base_url，简化子类调用；
        3. 每次请求都写入 Allure 报告：请求 / 响应正文附件、状态码、耗时；
        4. 提供统一的 :meth:`assert_status` 断言入口。
    """

    #: 子类可覆盖默认地址
    base_url: str = DEFAULT_BASE_URL
    #: 请求超时时间（连接, 读取）
    timeout: tuple = (5, 30)

    def __init__(
        self,
        base_url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[tuple] = None,
    ) -> None:
        self.base_url = (base_url or self.base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        if headers:
            self.session.headers.update(headers)
        LOGGER.debug("初始化 BaseAPI: base_url=%s", self.base_url)

    # ------------------------------------------------------------------ #
    # 对外能力
    # ------------------------------------------------------------------ #
    def set_token(self, token: str, scheme: str = "Bearer") -> None:
        """登录成功后写入 Authorization 头，供后续需要鉴权的接口使用。"""
        self.session.headers["Authorization"] = f"{scheme} {token}"

    def clear_token(self) -> None:
        """移除 Authorization 头。"""
        self.session.headers.pop("Authorization", None)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Any = None,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[tuple] = None,
    ) -> requests.Response:
        """发送 HTTP 请求，并自动把请求 / 响应写入 Allure 报告。

        Args:
            method: HTTP 方法，如 ``GET`` / ``POST``。
            path: 相对路径（如 ``/products/1``）或完整 URL。
            params: URL 查询参数。
            json_body: 请求体（自动序列化为 JSON）。
            data: 请求体（表单或原始字符串）。
            headers: 本次请求追加的请求头。
            timeout: 覆盖默认超时。

        Returns:
            ``requests.Response`` 对象。
        """
        method = method.upper()
        url = path if path.startswith("http") else urljoin(f"{self.base_url}/", path.lstrip("/"))
        request_kwargs: Dict[str, Any] = {
            "params": params,
            "json": json_body,
            "data": data,
            "headers": headers,
            "timeout": timeout or self.timeout,
        }
        step_title = f"{method} {url}"

        with allure.step(step_title):
            self._attach_request(method, url, params, json_body, data, headers)
            LOGGER.info("--> %s %s params=%s body=%s", method, url, params, _sanitize(json_body or data or {}))
            response = self.session.request(method, url, **request_kwargs)
            LOGGER.info("<-- %s %s %s (%d ms)", method, url, response.status_code, response.elapsed.total_seconds() * 1000)
            self._attach_response(response)
            return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        """发送 GET 请求。"""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        """发送 POST 请求。"""
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        """发送 PUT 请求。"""
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        """发送 DELETE 请求。"""
        return self.request("DELETE", path, **kwargs)

    def close(self) -> None:
        """关闭底层会话，释放连接资源。"""
        self.session.close()

    # ------------------------------------------------------------------ #
    # 内部辅助
    # ------------------------------------------------------------------ #
    def _attach_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]],
        json_body: Any,
        data: Any,
        headers: Optional[Dict[str, str]],
    ) -> None:
        """把请求信息作为附件写入 Allure 报告。"""
        request_info = {
            "method": method,
            "url": url,
            "params": params,
            "headers": _sanitize(dict(self.session.headers)),
            "extra_headers": _sanitize(headers or {}),
            "body": _sanitize(json_body if json_body is not None else data),
        }
        allure.attach(
            _truncate(_to_pretty_json(request_info)),
            name="请求信息",
            attachment_type=allure.attachment_type.JSON,
        )

    def _attach_response(self, response: requests.Response) -> None:
        """把响应信息作为附件写入 Allure 报告。"""
        try:
            body = response.json()
        except ValueError:
            body = response.text

        response_info = {
            "status_code": response.status_code,
            "reason": response.reason,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 2),
            "url": response.url,
            "body": body,
        }
        allure.attach(
            _truncate(_to_pretty_json(response_info)),
            name=f"响应信息 (HTTP {response.status_code})",
            attachment_type=allure.attachment_type.JSON,
        )

    # ------------------------------------------------------------------ #
    # 断言辅助
    # ------------------------------------------------------------------ #
    @staticmethod
    def assert_status(response: requests.Response, expected: Any = 200) -> None:
        """断言响应状态码。

        Args:
            response: 响应对象。
            expected: 期望状态码，可以是 int、int 列表或 tuple。
        """
        expected_codes = (expected,) if isinstance(expected, int) else tuple(expected)
        assert response.status_code in expected_codes, (
            f"状态码断言失败：期望 {list(expected_codes)}，实际 {response.status_code}；"
            f"响应内容：{response.text[:500]}"
        )

    @staticmethod
    def json_body(response: requests.Response) -> Any:
        """安全地解析响应 JSON。

        * 响应体为空时返回 ``None``（Fake Store API 对不存在的资源返回 200 + 空响应体）；
        * 响应体不是合法 JSON 时抛出带上下文信息的 ``AssertionError``。
        """
        if not response.text or not response.text.strip():
            return None
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - 仅用于错误提示
            raise AssertionError(f"响应不是合法 JSON：{response.text[:500]}") from exc

    # ------------------------------------------------------------------ #
    # 环境变量便捷方法
    # ------------------------------------------------------------------ #
    @classmethod
    def from_env(cls) -> "BaseAPI":
        """根据环境变量 ``API_BASE_URL`` 创建实例，方便切换测试环境。"""
        return cls(base_url=os.getenv("API_BASE_URL", DEFAULT_BASE_URL))
