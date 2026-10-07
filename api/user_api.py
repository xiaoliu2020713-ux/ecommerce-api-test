"""用户相关接口封装：登录、查询用户信息。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base_api import BaseAPI


class UserAPI(BaseAPI):
    """Fake Store API 用户模块。

    涉及接口：
        * ``POST /auth/login``  用户登录并获取 token
        * ``GET  /users/{id}``  查询单个用户信息
        * ``GET  /users``       查询全部用户（辅助接口）
    """

    LOGIN_PATH = "/auth/login"
    USER_PATH = "/users/{user_id}"

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录。

        Args:
            username: 用户名，例如官方测试账号 ``mor_2314``。
            password: 密码。

        Returns:
            登录成功的响应 JSON，形如 ``{"token": "..."}``。

        Note:
            Fake Store API 登录成功返回 **201**，账号密码错误返回 **401**。
        """
        payload = {"username": username, "password": password}
        response = self.post(self.LOGIN_PATH, json_body=payload)
        return self.json_body(response)

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """根据用户 ID 查询用户详情。"""
        response = self.get(self.USER_PATH.format(user_id=user_id))
        return self.json_body(response)

    def get_all_users(self) -> list:
        """查询全部用户（辅助接口，用于数据校验）。"""
        response = self.get("/users")
        return self.json_body(response)

    def get_token(self, username: str, password: str, scheme: str = "Bearer") -> str:
        """登录并把 token 写入会话请求头，返回 token 字符串。"""
        token = self.login(username, password).get("token", "")
        if token:
            self.set_token(token, scheme=scheme)
        return token

    def login_response(self, username: str, password: str):
        """返回原始响应对象，便于对错误状态码（如 401）做断言。"""
        return self.post(self.LOGIN_PATH, json_body={"username": username, "password": password})

    def login_with_payload(self, payload: Optional[Dict[str, Any]] = None, **kwargs: Any):
        """使用自定义请求体调用登录接口，便于参数化异常场景。"""
        body = payload if payload is not None else kwargs
        return self.post(self.LOGIN_PATH, json_body=body)
