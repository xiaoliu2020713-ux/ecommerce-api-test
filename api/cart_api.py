"""购物车相关接口封装：查询购物车、添加购物车。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_api import BaseAPI


class CartAPI(BaseAPI):
    """Fake Store API 购物车模块。

    涉及接口：
        * ``GET  /carts/{id}``        查询单个购物车
        * ``POST /carts``             新增购物车
        * ``GET  /carts/user/{id}``   查询某用户的全部购物车（辅助接口）
    """

    CART_PATH = "/carts/{cart_id}"
    CARTS_PATH = "/carts"
    USER_CARTS_PATH = "/carts/user/{user_id}"

    def get_cart(self, cart_id: int) -> Dict[str, Any]:
        """查询指定购物车详情。"""
        response = self.get(self.CART_PATH.format(cart_id=cart_id))
        return self.json_body(response)

    def add_to_cart(self, user_id: int, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """新增购物车（把商品加入指定用户）。

        Args:
            user_id: 用户 ID。
            products: 商品明细列表，形如
                ``[{"productId": 1, "quantity": 2}, {"productId": 5, "quantity": 1}]``。

        Returns:
            新增结果，形如
            ``{"id": 11, "userId": 1, "date": "...", "products": [...]}``。

        Note:
            Fake Store API 是模拟服务，写接口只返回创建结果，不会真正落库，
            因此断言集中在响应结构、回显数据与新生成的主键 ID 上。
        """
        payload = {
            "userId": user_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "products": products,
        }
        response = self.post(self.CARTS_PATH, json_body=payload)
        return self.json_body(response)

    def add_to_cart_response(self, user_id: int, products: List[Dict[str, Any]]):
        """返回原始响应对象，便于对状态码做断言。"""
        payload = {
            "userId": user_id,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "products": products,
        }
        return self.post(self.CARTS_PATH, json_body=payload)

    def get_carts_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """查询某个用户的全部购物车（辅助接口）。"""
        response = self.get(self.USER_CARTS_PATH.format(user_id=user_id))
        return self.json_body(response)

    def build_product_item(self, product_id: int, quantity: int = 1) -> Dict[str, int]:
        """构造单条购物车商品明细。"""
        if quantity <= 0:
            raise ValueError("quantity 必须为正整数")
        return {"productId": product_id, "quantity": quantity}

    def get_cart_or_none(self, cart_id: int) -> Optional[Dict[str, Any]]:
        """查询购物车，不存在时返回 ``None``。

        Note:
            Fake Store API 对不存在的购物车返回 **200 且响应体为 null**（而非 404），
            因此这里把「空响应体」统一归一化为 ``None``。
        """
        response = self.get(self.CART_PATH.format(cart_id=cart_id))
        if response.status_code == 404:
            return None
        return self.json_body(response) or None
