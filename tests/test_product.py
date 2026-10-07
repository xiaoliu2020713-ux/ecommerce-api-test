"""商品模块接口测试：商品列表、商品详情、按分类查询商品。"""

from __future__ import annotations

import allure
import pytest

pytestmark = [pytest.mark.product]


@allure.feature("商品模块")
class TestProduct:
    """商品模块用例集。"""

    @allure.story("商品查询")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @allure.title("查询全部商品：GET /products 返回完整商品列表")
    @allure.description(
        "调用 GET /products 查询全部商品，校验状态码 200、"
        "返回列表长度为 20、每个商品都包含必要字段且价格大于 0。"
    )
    def test_get_all_products(self, product_api, test_data):
        """正向用例：查询全部商品。"""
        expected_total = test_data["products"]["expected_total"]
        expected_fields = test_data["products"]["expected_detail_fields"]

        with allure.step("步骤1：调用查询全部商品接口 GET /products"):
            response = product_api.get_all_products_response()
            product_api.assert_status(response, 200)

        with allure.step("步骤2：校验返回结果是列表且数量符合预期"):
            products = product_api.json_body(response)
            assert isinstance(products, list), f"响应不是列表：{type(products)}"
            assert len(products) == expected_total, (
                f"商品数量不符：期望 {expected_total}，实际 {len(products)}"
            )

        with allure.step("步骤3：校验每个商品的字段完整性与价格合法性"):
            for product in products:
                missing = [field for field in expected_fields if field not in product]
                assert not missing, f"商品 {product.get('id')} 缺少字段：{missing}"
                assert product["price"] > test_data["products"]["min_price"], (
                    f"商品 {product['id']} 价格不合法：{product['price']}"
                )

        with allure.step("步骤4：校验商品 ID 唯一"):
            ids = [product["id"] for product in products]
            assert len(ids) == len(set(ids)), "商品 ID 存在重复"

        allure.attach(
            f"商品总数: {len(products)}\n商品 ID: {sorted(ids)}",
            name="商品列表概览",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("查询商品详情：GET /products/{id} 返回指定商品")
    @allure.description(
        "参数化调用 GET /products/{id}，校验状态码 200、"
        "返回的商品 ID 与请求一致、关键字段完整且标题非空。"
    )
    @pytest.mark.parametrize("product_id", [1, 2, 5])
    def test_get_product_detail(self, product_api, test_data, product_id):
        """正向用例：查询单个商品详情。"""
        expected_fields = test_data["products"]["expected_detail_fields"]

        with allure.step(f"步骤1：调用商品详情接口 GET /products/{product_id}"):
            response = product_api.get(f"/products/{product_id}")
            product_api.assert_status(response, 200)

        with allure.step("步骤2：校验商品 ID 与请求参数一致"):
            product = product_api.json_body(response)
            assert product["id"] == product_id, (
                f"商品 ID 不一致：期望 {product_id}，实际 {product['id']}"
            )

        with allure.step("步骤3：校验商品关键字段完整且取值合法"):
            missing = [field for field in expected_fields if field not in product]
            assert not missing, f"商品详情缺少字段：{missing}"
            assert isinstance(product["title"], str) and product["title"].strip(), "商品标题不能为空"
            assert product["price"] > 0, f"商品价格必须大于 0，实际 {product['price']}"
            assert product["image"].startswith("http"), f"商品图片地址不合法：{product['image']}"

        with allure.step("步骤4：校验接口支持按 ID 精确定位（与列表接口数据一致）"):
            all_products = product_api.get_all_products()
            matched = [item for item in all_products if item["id"] == product_id]
            assert matched, f"列表接口中找不到商品 {product_id}"
            assert matched[0]["title"] == product["title"], "详情接口与列表接口返回的标题不一致"

        allure.attach(
            f"product_id={product_id}\ntitle={product['title']}\n"
            f"price={product['price']}\ncategory={product['category']}",
            name="商品详情",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("分类查询")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("按分类查询商品：GET /products/category/{category} 返回该分类商品")
    @allure.description(
        "参数化调用 GET /products/category/{category}，校验状态码 200、"
        "返回非空列表且每个商品的 category 与请求分类一致。"
    )
    @pytest.mark.parametrize(
        "category",
        ["electronics", "jewelery", "men's clothing", "women's clothing"],
    )
    def test_get_products_by_category(self, product_api, test_data, category):
        """正向用例：按分类查询商品。"""
        with allure.step(f"步骤1：调用分类查询接口，category={category}"):
            response = product_api.get(
                f"/products/category/{category}"
            )
            product_api.assert_status(response, 200)

        with allure.step("步骤2：校验返回非空列表"):
            products = product_api.json_body(response)
            assert isinstance(products, list), f"响应不是列表：{type(products)}"
            assert products, f"分类 {category} 未查询到任何商品"

        with allure.step("步骤3：校验每个商品归属该分类"):
            categories = {product["category"] for product in products}
            assert categories == {category}, (
                f"返回商品分类不匹配：期望 {category}，实际 {categories}"
            )

        with allure.step("步骤4：校验分类存在于分类列表中"):
            all_categories = product_api.get_categories()
            assert category in all_categories, f"分类 {category} 不在分类列表 {all_categories} 中"

        allure.attach(
            f"category={category}\n商品数量={len(products)}\n"
            f"商品 ID={[product['id'] for product in products]}",
            name="分类查询结果",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("商品查询")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("异常场景：查询不存在的商品返回空数据")
    @allure.description(
        "请求不存在的商品 ID。\n"
        "说明：Fake Store API 对不存在的商品并不返回 404，而是返回 **200 + 空响应体**，"
        "用例按该服务端实际契约断言：不报错、不返回商品数据，"
        "并校验辅助方法 get_product_or_none 归一化为 None。"
    )
    def test_get_product_not_found(self, product_api):
        """反向用例：查询不存在的商品。"""
        missing_id = 999999

        with allure.step(f"步骤1：请求一个不存在的商品 ID（{missing_id}）"):
            response = product_api.get(f"/products/{missing_id}")

        with allure.step("步骤2：校验服务端未返回 5xx 错误"):
            assert response.status_code < 500, (
                f"查询不存在的商品不应返回服务端错误，实际 {response.status_code}"
            )

        with allure.step("步骤3：校验响应体为空，未返回商品数据"):
            body = product_api.json_body(response)
            assert not body, f"不存在的商品却返回了数据：{body}"

        with allure.step("步骤4：校验 get_product_or_none 归一化返回 None"):
            assert product_api.get_product_or_none(missing_id) is None, (
                "不存在的商品应归一化为 None"
            )
