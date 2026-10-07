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
# 接口对象 fixture
# ---------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def user_api(base_url: str):
    """用户模块接口对象。"""
    api = UserAPI(base_url=base_url)
    yield api
    api.close()


@pytest.fixture(scope="session")
def product_api(base_url: str):
    """商品模块接口对象。"""
    api = ProductAPI(base_url=base_url)
    yield api
    api.close()


@pytest.fixture(scope="session")
def cart_api(base_url: str):
    """购物车模块接口对象。"""
    api = CartAPI(base_url=base_url)
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
def allure_environment(base_url: str) -> None:
    """生成 Allure 报告所需的 environment.properties。"""
    results_dir = PROJECT_ROOT / "reports" / "allure-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    properties = {
        "Base.URL": base_url,
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
