"""pytest 全局配置与公共 fixture。

提供：
    * ``test_data``        —— 加载 ``data/test_data.yaml`` 测试数据
    * ``base_url``         —— 被测系统地址
    * ``user_api``         —— 用户模块接口对象（session 级）
    * ``product_api``      —— 商品模块接口对象（session 级）
    * ``cart_api``         —— 购物车模块接口对象（session 级）
    * ``login_token``      —— 使用官方测试账号登录后得到的 token（session 级）
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import allure
import pytest
import requests
import yaml

# 保证以项目根目录为导入起点，直接 `pytest` 即可运行
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api import CartAPI, ProductAPI, UserAPI  # noqa: E402

LOGGER = logging.getLogger("ecommerce_api_test")

#: 测试数据文件
DATA_FILE = PROJECT_ROOT / "data" / "test_data.yaml"

#: 默认被测地址
DEFAULT_BASE_URL = "https://fakestoreapi.com"


# ---------------------------------------------------------------------- #
# 会话级配置
# ---------------------------------------------------------------------- #
def pytest_addoption(parser: pytest.Parser) -> None:
    """新增命令行参数，便于切换测试环境。"""
    parser.addini("base_url", "被测试系统的基础地址", default=DEFAULT_BASE_URL)
    parser.addoption(
        "--base-url",
        action="store",
        default=None,
        help="被测系统基础地址，例如 --base-url=https://fakestoreapi.com",
    )
    parser.addoption(
        "--api-mode",
        action="store",
        default=os.getenv("API_MODE", "live"),
        choices=("live", "mock", "auto"),
        help=(
            "测试目标模式：live=真实 Fake Store API（默认）；"
            "mock=启动本地 Mock 服务（云 CI 被 Cloudflare 拦截时使用）；"
            "auto=先探测真实接口，被拦截或不可达时自动降级为 mock"
        ),
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig: pytest.Config) -> str:
    """被测系统基础地址：命令行/环境变量 > pytest.ini > 默认值。"""
    return (
        pytestconfig.getoption("--base-url", default=None)
        or os.getenv("API_BASE_URL")
        or pytestconfig.getini("base_url")
        or DEFAULT_BASE_URL
    )


@pytest.fixture(scope="session")
def test_data() -> Dict[str, Any]:
    """加载 YAML 测试数据，整个测试会话只读取一次。"""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"测试数据文件不存在：{DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    LOGGER.info("已加载测试数据：%s", DATA_FILE)
    return data


# ---------------------------------------------------------------------- #
# 测试目标解析：真实 API / 本地 Mock
# ---------------------------------------------------------------------- #
#: 云 CI（如 GitHub Actions）运行在数据中心 IP 上，会被 Cloudflare 机器人防护拦截，
#: 返回 403 + "Just a moment..." 挑战页，因此提供本地 Mock 作为 CI 的稳定测试目标。
#: 注意：探测必须打真实业务接口（/products），不能打站点根路径（/），
#: 根路径返回的是正常 HTML 落地页，并不代表接口可用。
CLOUDFLARE_MARKERS = ("just a moment", "cf-chl", "enable javascript and cookies")

#: 探测用的业务接口路径
PROBE_PATH = "/products"

#: 本地 Mock 服务的进程内单例
_MOCK_SERVER = None
_MOCK_BASE_URL: str | None = None


def _external_api_is_blocked(base_url: str, timeout: float = 15.0) -> bool:
    """探测真实接口是否被 Cloudflare 挑战页拦截或不可达。

    探测目标是真实业务接口 ``{base_url}/products``，判定依据：

    * 请求抛异常（DNS / 连接失败 / 超时）→ 视为不可用；
    * 状态码为 403 / 429 / 503（Cloudflare 拦截的典型返回）→ 视为被拦截；
    * 响应体包含 Cloudflare 挑战页特征，或不是合法 JSON、列表为空
      （挑战页是 HTML，正常接口是商品 JSON 数组）→ 视为被拦截。
    """
    url = base_url.rstrip("/") + PROBE_PATH
    try:
        response = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        LOGGER.warning("真实接口不可达：%s（%s）", url, exc)
        return True

    if response.status_code in (403, 429, 503):
        LOGGER.warning("真实接口被拦截：%s 返回 %s", url, response.status_code)
        return True

    body = (response.text or "").lower()
    if any(marker in body for marker in CLOUDFLARE_MARKERS):
        LOGGER.warning("真实接口返回 Cloudflare 挑战页：%s", url)
        return True

    try:
        payload = response.json()
    except ValueError:
        LOGGER.warning("真实接口返回的不是 JSON（疑似挑战页）：%s", url)
        return True

    if not isinstance(payload, list) or not payload:
        LOGGER.warning("真实接口未返回预期的商品列表：%s", url)
        return True

    return False


def _ensure_mock_server() -> str:
    """启动（或复用）本地 Mock 服务，返回其 base_url。"""
    global _MOCK_SERVER, _MOCK_BASE_URL
    if _MOCK_SERVER is None:
        from sandbox.mock_server import start_mock_server

        _MOCK_SERVER, _MOCK_BASE_URL = start_mock_server()
        LOGGER.info("已启动本地 Mock 服务：%s", _MOCK_BASE_URL)
    return _MOCK_BASE_URL


@pytest.fixture(scope="session")
def api_mode(pytestconfig: pytest.Config) -> str:
    """当前测试目标模式：live / mock / auto。"""
    return pytestconfig.getoption("--api-mode")


@pytest.fixture(scope="session")
def api_target_uri(base_url: str, api_mode: str) -> str:
    """解析本次测试实际访问的地址。

    * ``live``：访问真实 API；若被 Cloudflare 拦截或不可达，则跳过全部用例并给出提示；
    * ``mock``：启动本地 Mock 服务，地址指向 ``127.0.0.1``；
    * ``auto``：优先真实 API，被拦截时自动降级为 Mock。
    """
    mock_mode = api_mode == "mock"
    if mock_mode:
        allure.attach(
            f"测试目标模式：{api_mode}\n本次使用本地 Mock 服务作为被测对象。",
            name="测试目标",
            attachment_type=allure.attachment_type.TEXT,
        )
        return _ensure_mock_server()

    blocked = _external_api_is_blocked(base_url)

    if blocked and api_mode == "auto":
        allure.attach(
            f"真实接口 {base_url} 不可用（被 Cloudflare 拦截或网络不通），"
            f"本次自动降级为本地 Mock 服务。",
            name="测试目标",
            attachment_type=allure.attachment_type.TEXT,
        )
        return _ensure_mock_server()

    if blocked:
        pytest.skip(
            f"真实接口 {base_url} 当前不可用（被 Cloudflare 机器人防护拦截或网络不通）。"
            f"这是运行环境限制，不是用例缺陷：本地可正常执行，"
            f"云 CI（如 GitHub Actions）请使用 --api-mode=mock 或 --api-mode=auto。"
        )

    allure.attach(
        f"测试目标模式：{api_mode}\n被测地址：{base_url}",
        name="测试目标",
        attachment_type=allure.attachment_type.TEXT,
    )
    return base_url


@pytest.fixture(scope="session")
def resolved_base_url(api_target_uri: str) -> str:
    """本次测试会话最终使用的被测地址。"""
    return api_target_uri


# ---------------------------------------------------------------------- #
# 接口对象 fixture
# ---------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def user_api(resolved_base_url: str):
    """用户模块接口对象。"""
    api = UserAPI(base_url=resolved_base_url)
    yield api
    api.close()


@pytest.fixture(scope="session")
def product_api(resolved_base_url: str):
    """商品模块接口对象。"""
    api = ProductAPI(base_url=resolved_base_url)
    yield api
    api.close()


@pytest.fixture(scope="session")
def cart_api(resolved_base_url: str):
    """购物车模块接口对象。"""
    api = CartAPI(base_url=resolved_base_url)
    yield api
    api.close()


# ---------------------------------------------------------------------- #
# 登录 token fixture
# ---------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def login_token(user_api: UserAPI, test_data: Dict[str, Any]) -> str:
    """使用官方测试账号登录，返回 JWT token。

    账号信息取自 ``data/test_data.yaml`` 的 ``login.valid`` 节点，
    默认值为 ``mor_2314 / 83r5^_``。
    """
    credentials = test_data.get("login", {}).get("valid", {})
    username = credentials.get("username", "mor_2314")
    password = credentials.get("password", "83r5^_")

    with allure.step(f"前置步骤：使用测试账号 {username} 登录并获取 token"):
        token = user_api.get_token(username, password)
        assert token, "登录失败：未获取到 token"
        allure.attach(token, name="登录 token", attachment_type=allure.attachment_type.TEXT)
        LOGGER.info("登录成功，token 前缀：%s...", token[:20])
    return token


@pytest.fixture(scope="session")
def authorized_user_api(user_api: UserAPI, login_token: str):
    """已带上 Authorization 头的用户接口对象（演示鉴权场景）。"""
    user_api.set_token(login_token)
    return user_api


# ---------------------------------------------------------------------- #
# Allure 环境信息
# ---------------------------------------------------------------------- #
@pytest.fixture(scope="session", autouse=True)
def allure_environment(resolved_base_url: str) -> None:
    """生成 Allure 报告所需的 environment.properties。"""
    results_dir = PROJECT_ROOT / "reports" / "allure-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    properties = {
        "Base.URL": resolved_base_url,
        "Python": sys.version.split()[0],
        "Platform": sys.platform,
        "Tester": "ecommerce_api_test",
        "Project": "ecommerce_api_test",
    }
    try:
        with (results_dir / "environment.properties").open("w", encoding="utf-8") as fp:
            for key, value in properties.items():
                fp.write(f"{key}={value}\n")
    except OSError as exc:  # pragma: no cover - 仅影响报告附加信息
        LOGGER.warning("写入 environment.properties 失败：%s", exc)


# ---------------------------------------------------------------------- #
# 用例标记
# ---------------------------------------------------------------------- #
def pytest_collection_modifyitems(items) -> None:
    """为所有用例自动打上 ``api`` 标记。"""
    for item in items:
        item.add_marker(pytest.mark.api)
