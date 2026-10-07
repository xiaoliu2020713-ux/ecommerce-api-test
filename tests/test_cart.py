"""购物车模块接口测试：查询购物车、添加购物车。"""

from __future__ import annotations

import allure
import pytest

pytestmark = [pytest.mark.cart]


@allure.feature("购物车模块")
class TestCart:
    """购物车模块用例集。"""

    @allure.story("购物车查询")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.title("查询购物车：GET /carts/{id} 返回购物车详情")
    @allure.description(
        "参数化调用 GET /carts/{id}，校验状态码 200、"
        "购物车 ID 与请求一致、字段完整、商品明细结构合法且数量为正整数。"
    )
    @pytest.mark.parametrize("cart_id", [1, 2])
    def test_get_cart(self, cart_api, test_data, cart_id):
        """正向用例：查询购物车详情。"""
        expected_fields = test_data["cart"]["expected_fields"]

        with allure.step(f"步骤1：调用购物车详情接口 GET /carts/{cart_id}"):
            response = cart_api.get(f"/carts/{cart_id}")
            cart_api.assert_status(response, 200)

        with allure.step("步骤2：校验购物车字段完整"):
            cart = cart_api.json_body(response)
            missing = [field for field in expected_fields if field not in cart]
            assert not missing, f"购物车缺少字段：{missing}"

        with allure.step("步骤3：校验购物车 ID 与请求一致"):
            assert cart["id"] == cart_id, f"购物车 ID 不一致：期望 {cart_id}，实际 {cart['id']}"

        with allure.step("步骤4：校验商品明细结构合法（productId 为正整数、quantity > 0）"):
            products = cart["products"]
            assert isinstance(products, list) and products, "购物车商品明细不能为空"
            for item in products:
                assert {"productId", "quantity"} <= set(item), f"商品明细字段缺失：{item}"
                assert item["productId"] > 0, f"productId 非法：{item}"
                assert item["quantity"] > 0, f"quantity 必须为正整数：{item}"

        with allure.step("步骤5：校验同一用户的购物车查询接口数据自洽"):
            user_carts = cart_api.get_carts_by_user(cart["userId"])
            assert any(item["id"] == cart_id for item in user_carts), (
                f"用户 {cart['userId']} 的购物车列表中找不到购物车 {cart_id}"
            )

        allure.attach(
            f"cart_id={cart_id}\nuser_id={cart['userId']}\n"
            f"商品明细={cart['products']}",
            name="购物车详情",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("加入购物车")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @allure.title("添加购物车：POST /carts 新增购物车并回显商品明细")
    @allure.description(
        "调用 POST /carts 为指定用户新增购物车，校验状态码 201（兼容 200）、"
        "返回新的购物车 ID、userId 与商品明细与请求一致、明细数量求和正确。\n"
        "说明：Fake Store API 为模拟服务，写操作不会真正落库，"
        "因此用例只校验创建结果本身，不校验后续 GET 的持久化结果。"
    )
    def test_add_to_cart(self, cart_api, test_data):
        """正向用例：新增购物车。"""
        cart_payload = test_data["cart"]["new_cart"]
        user_id = cart_payload["user_id"]
        products = cart_payload["products"]
        existing_ids = test_data["cart"]["existing_ids"]

        with allure.step(f"步骤1：调用新增购物车接口 POST /carts，user_id={user_id}"):
            response = cart_api.add_to_cart_response(user_id, products)

        with allure.step("步骤2：校验状态码为 201（创建成功，兼容 200）"):
            assert response.status_code in (200, 201), (
                f"状态码断言失败：期望 200/201，实际 {response.status_code}；"
                f"响应内容：{response.text[:300]}"
            )

        with allure.step("步骤3：校验响应回显 userId 与商品明细"):
            body = cart_api.json_body(response)
            assert body["userId"] == user_id, (
                f"userId 不一致：期望 {user_id}，实际 {body.get('userId')}"
            )
            assert body["products"] == products, (
                f"商品明细不一致：期望 {products}，实际 {body.get('products')}"
            )

        with allure.step("步骤4：校验返回了新的购物车 ID"):
            assert "id" in body, f"响应缺少购物车 id 字段：{body}"
            assert isinstance(body["id"], int) and body["id"] > 0, (
                f"购物车 ID 非法：{body.get('id')}"
            )
            assert body["id"] not in existing_ids, (
                f"新建购物车 ID {body['id']} 与已有购物车重复"
            )

        with allure.step("步骤5：校验商品明细汇总逻辑"):
            total_quantity = sum(item["quantity"] for item in body["products"])
            assert total_quantity == sum(item["quantity"] for item in products), "商品数量汇总不一致"
            assert total_quantity > 0, "购物车商品总数量必须大于 0"

        allure.attach(
            f"请求体: user_id={user_id}, products={products}\n"
            f"新购物车 ID: {body['id']}\n"
            f"商品总数量: {total_quantity}",
            name="新增购物车结果",
            attachment_type=allure.attachment_type.TEXT,
        )

    @allure.story("购物车查询")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("异常场景：查询不存在的购物车返回空数据")
    @allure.description(
        "请求不存在的购物车 ID。\n"
        "说明：Fake Store API 对不存在的购物车并不返回 404，而是返回 **200 + null**，"
        "用例按该服务端实际契约断言：不报错、不返回购物车数据，"
        "并校验辅助方法 get_cart_or_none 归一化为 None。"
    )
    def test_get_cart_not_found(self, cart_api):
        """反向用例：查询不存在的购物车。"""
        missing_id = 999999

        with allure.step(f"步骤1：请求一个不存在的购物车 ID（{missing_id}）"):
            response = cart_api.get(f"/carts/{missing_id}")

        with allure.step("步骤2：校验服务端未返回 5xx 错误"):
            assert response.status_code < 500, (
                f"查询不存在的购物车不应返回服务端错误，实际 {response.status_code}"
            )

        with allure.step("步骤3：校验响应体为空，未返回购物车数据"):
            body = cart_api.json_body(response)
            assert not body, f"不存在的购物车却返回了数据：{body}"

        with allure.step("步骤4：校验辅助方法 get_cart_or_none 返回 None"):
            assert cart_api.get_cart_or_none(missing_id) is None, "不存在的购物车应返回 None"
