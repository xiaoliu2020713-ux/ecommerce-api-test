"""商品相关接口封装：商品列表、商品详情、按分类查询商品。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base_api import BaseAPI


class ProductAPI(BaseAPI):
    """Fake Store API 商品模块。

    涉及接口：
        * ``GET /products``                     查询全部商品
        * ``GET /products/{id}``                查询商品详情
        * ``GET /products/category/{category}`` 按分类查询商品
        * ``GET /products/categories``          查询分类列表（辅助接口）
    """

    PRODUCTS_PATH = "/products"
    PRODUCT_DETAIL_PATH = "/products/{product_id}"
    PRODUCTS_BY_CATEGORY_PATH = "/products/category/{category}"

    def get_all_products(self) -> List[Dict[str, Any]]:
        """查询全部商品，返回商品列表。"""
        response = self.get(self.PRODUCTS_PATH)
        return self.json_body(response)

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """查询指定商品详情。"""
        response = self.get(self.PRODUCT_DETAIL_PATH.format(product_id=product_id))
        return self.json_body(response)

    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """按分类查询商品，返回该分类下的商品列表。

        Args:
            category: 分类名称，例如 ``electronics``、``jewelery``。
                      含空格或特殊字符时由 requests 自动完成 URL 编码。
        """
        response = self.get(self.PRODUCTS_BY_CATEGORY_PATH.format(category=category))
        return self.json_body(response)

    def get_categories(self) -> List[str]:
        """查询全部商品分类（辅助接口）。"""
        response = self.get("/products/categories")
        return self.json_body(response)

    def get_all_products_response(self):
        """返回原始响应对象，便于对状态码、响应头做断言。"""
        return self.get(self.PRODUCTS_PATH)

    def get_product_or_none(self, product_id: int) -> Optional[Dict[str, Any]]:
        """查询商品，商品不存在时返回 ``None``。

        Note:
            Fake Store API 对不存在的商品返回 **200 且响应体为空**（而非 404），
            因此这里把「空响应体」统一归一化为 ``None``。
        """
        response = self.get(self.PRODUCT_DETAIL_PATH.format(product_id=product_id))
        if response.status_code == 404:
            return None
        return self.json_body(response) or None

