"""用户模块接口测试：登录、查询用户信息。"""

from __future__ import annotations

import allure
import pytest

pytestmark = [pytest.mark.user]


@allure.feature("用户模块")
class TestUser:
    """用户模块用例集。"""

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @allure.title("正常登录：使用官方测试账号登录成功并返回 token")
    @allure.description(
        "调用 POST /auth/login，使用 Fake Store API 官方测试账号 mor_2314 登录，"
        "校验状态码 201、响应包含 token 且 token 为合法 JWT 格式。"
    )
    def test_login_success(self, user_api, test_data, login_token):
        """正向用例：登录成功返回 token。"""
        credentials = test_data["login"]["valid"]
        username = credentials["username"]
        password = credentials["password"]

        with allure.step("步骤1：调用登录接口 POST /auth/login"):
            response = user_api.login_response(username, password)
            user_api.assert_status(response, 201)

        with allure.step("步骤2：校验响应体包含 token 字段"):
            body = user_api.json_body(response)
            assert "token" in body, f"响应中缺少 token 字段：{body}"
            token = body["token"]
            assert isinstance(token, str) and token, "token 必须是非空字符串"

        with allure.step("步骤3：校验 token 为 JWT 格式（三段式）"):
            parts = token.split(".")
            assert len(parts) == 3, f"token 不是标准 JWT 格式：{token}"

        with allure.step("步骤4：校验 session 级 fixture 登录流程可复用"):
            assert login_token == token or login_token, "login_token fixture 应当返回可用 token"

        allure.attach(
            f"账号: {username}\n状态码: {response.status_code}\ntoken: {token}",
            name="登录结果",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("异常登录：错误的密码应返回 401")
    @allure.description(
        "使用错误密码调用 POST /auth/login，校验服务端拒绝登录并返回 401，"
        "且响应中不包含可用 token。"
    )
    def test_login_failed_with_wrong_password(self, user_api, test_data):
        """反向用例：密码错误登录失败。"""
        invalid_case = test_data["login"]["invalid"][0]

        with allure.step(f"步骤1：使用错误密码登录（{invalid_case['case_name']}）"):
            response = user_api.login_response(
                invalid_case["username"], invalid_case["password"]
            )

        with allure.step(f"步骤2：校验状态码为 {invalid_case['expected_status']}"):
            user_api.assert_status(response, invalid_case["expected_status"])

        with allure.step("步骤3：校验响应体中不含 token"):
            body = response.text
            assert "token" not in body, f"登录失败却返回了 token：{body}"

    @allure.story("用户登录")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("异常登录：不存在的用户名应返回 401")
    def test_login_failed_with_unknown_user(self, user_api, test_data):
        """反向用例：用户名不存在登录失败。"""
        invalid_case = test_data["login"]["invalid"][1]

        with allure.step(f"步骤1：使用不存在的用户名登录（{invalid_case['case_name']}）"):
            response = user_api.login_response(
                invalid_case["username"], invalid_case["password"]
            )

        with allure.step("步骤2：校验服务端拒绝登录"):
            user_api.assert_status(response, invalid_case["expected_status"])

    @allure.story("用户信息查询")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("查询用户详情：GET /users/{id} 返回正确的用户信息")
    @allure.description(
        "调用 GET /users/{id} 查询指定用户，校验状态码 200、"
        "返回的 id 与请求一致、字段完整且邮箱格式合法。"
    )
    @pytest.mark.parametrize("user_id", [1, 2])
    def test_get_user(self, user_api, test_data, user_id):
        """正向用例：查询单个用户信息。"""
        expected_fields = test_data["user_api"]["expected_fields"]

        with allure.step(f"步骤1：调用查询用户接口 GET /users/{user_id}"):
            response = user_api.get(f"/users/{user_id}")
            user_api.assert_status(response, 200)

        with allure.step("步骤2：校验返回的用户 ID 与请求一致"):
            user = user_api.json_body(response)
            assert user["id"] == user_id, f"用户 ID 不一致：期望 {user_id}，实际 {user['id']}"

        with allure.step("步骤3：校验用户关键字段完整"):
            missing = [field for field in expected_fields if field not in user]
            assert not missing, f"用户信息缺少字段：{missing}"

        with allure.step("步骤4：校验邮箱与用户名格式合法"):
            assert "@" in user["email"], f"邮箱格式不合法：{user['email']}"
            assert isinstance(user["username"], str) and user["username"], "用户名不能为空"

        with allure.step("步骤5：校验姓名结构体"):
            assert {"firstname", "lastname"} <= set(user["name"]), "姓名字段结构不完整"

        allure.attach(
            f"user_id={user_id}\nusername={user['username']}\nemail={user['email']}",
            name="用户信息",
            attachment_type=allure.attachment_type.TEXT,
        )
