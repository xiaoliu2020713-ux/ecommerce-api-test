# 测试用例清单（共 18 条）

本文档是本项目全部接口测试用例的**完整清单**，可用于评审、答疑和面试讲解。

- 清单与仓库代码**逐条对应**，代码位置：`tests/test_user.py`、`tests/test_product.py`、`tests/test_cart.py`
- 在线执行结果：<https://xiaoliu2020713-ux.github.io/ecommerce-api-test/>

---

## 一、总览

| 统计口径 | 数量 | 说明 |
| --- | --- | --- |
| 测试函数（代码里 `def test_` 的个数） | **11 个** | 代码组织单位 |
| 其中做了参数化的函数 | 4 个 | 一份代码覆盖多组数据 |
| **实际执行用例（报告里的用例数）** | **18 条** | 本清单列出的就是这 18 条 |
| Allure 报告中的「用例名」条目 | 7 个 | 参数化用例共用同一个标题 |

**按业务模块**

| 模块 | 测试文件 | 用例数 | 占比 |
| --- | --- | --- | --- |
| 用户模块 | `tests/test_user.py` | 5 | 28% |
| 商品模块 | `tests/test_product.py` | 9 | 50% |
| 购物车模块 | `tests/test_cart.py` | 4 | 22% |
| **合计** | | **18** | 100% |

**按测试类型**

| 类型 | 数量 | 用例编号 |
| --- | --- | --- |
| ✅ 正向（正常业务流程） | **14** | 1、4~13、15~17 |
| ❌ 反向（异常与边界） | **4** | 2、3、14、18 |

**按优先级（Allure 严重级别）**

| 级别 | 数量 | 用例编号 |
| --- | --- | --- |
| 🔴 BLOCKER（阻塞级，挂了核心链路就走不通） | **5** | 1、6、15、16、17 |
| 🟠 CRITICAL（严重级） | **10** | 2、4、5、7~13 |
| 🟡 NORMAL（一般级） | **3** | 3、14、18 |

**冒烟用例（`pytest -m smoke`，3 条）**
编号 1（登录）、6（商品列表）、17（加购物车）—— 覆盖「登录 → 看商品 → 下单」主干，改完代码先跑这 3 条快速回归。

---

## 二、用户模块（5 条）

| # | 测试函数 | 用例名 | 接口 | 方法 | 类型 | 级别 | 核心断言 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `test_login_success` | 正常登录：使用官方测试账号登录成功并返回 token | `/auth/login` | POST | ✅ 正向 | 🔴 BLOCKER | 状态码 **201**；响应含 `token`；token 为三段式 JWT 格式；session 级 `login_token` 可复用 |
| 2 | `test_login_failed_with_wrong_password` | 异常登录：错误的密码应返回 401 | `/auth/login` | POST | ❌ 反向 | 🟠 CRITICAL | 状态码 **401**；响应体中**不含** token |
| 3 | `test_login_failed_with_unknown_user` | 异常登录：不存在的用户名应返回 401 | `/auth/login` | POST | ❌ 反向 | 🟡 NORMAL | 状态码 **401** |
| 4 | `test_get_user[1]` | 查询用户详情 | `/users/1` | GET | ✅ 正向 | 🟠 CRITICAL | 状态码 200；ID 与请求一致；字段完整；邮箱含 `@`；姓名结构齐全 |
| 5 | `test_get_user[2]` | 查询用户详情（参数化第 2 组） | `/users/2` | GET | ✅ 正向 | 🟠 CRITICAL | 同上 |

> **参数化**：编号 4、5 由同一个函数 `test_get_user` 展开，`@pytest.mark.parametrize("user_id", [1, 2])`。

---

## 三、商品模块（9 条）

| # | 测试函数 | 用例名 | 接口 | 方法 | 类型 | 级别 | 核心断言 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | `test_get_all_products` | 查询全部商品：返回完整商品列表 | `/products` | GET | ✅ 正向 | 🔴 BLOCKER | 状态码 200；**恰好 20 条**；字段完整；价格 > 0；**ID 不重复** |
| 7 | `test_get_product_detail[1]` | 查询商品详情 | `/products/1` | GET | ✅ 正向 | 🟠 CRITICAL | 状态码 200；ID 一致；字段完整；标题非空；价格 > 0；图片为 http 地址；**与列表接口数据一致** |
| 8 | `test_get_product_detail[2]` | 查询商品详情（参数化第 2 组） | `/products/2` | GET | ✅ 正向 | 🟠 CRITICAL | 同上 |
| 9 | `test_get_product_detail[5]` | 查询商品详情（参数化第 3 组） | `/products/5` | GET | ✅ 正向 | 🟠 CRITICAL | 同上 |
| 10 | `test_get_products_by_category[electronics]` | 按分类查询商品 | `/products/category/electronics` | GET | ✅ 正向 | 🟠 CRITICAL | 状态码 200；返回列表**非空**；**每个商品分类都等于请求分类**；该分类存在于分类列表中 |
| 11 | `test_get_products_by_category[jewelery]` | 按分类查询商品（参数化第 2 组） | `/products/category/jewelery` | GET | ✅ 正向 | 🟠 CRITICAL | 同上 |
| 12 | `test_get_products_by_category[men's clothing]` | 按分类查询商品（参数化第 3 组） | `/products/category/men's clothing` | GET | ✅ 正向 | 🟠 CRITICAL | 同上（分类名含**空格与单引号**，由 requests 自动 URL 编码） |
| 13 | `test_get_products_by_category[women's clothing]` | 按分类查询商品（参数化第 4 组） | `/products/category/women's clothing` | GET | ✅ 正向 | 🟠 CRITICAL | 同上 |
| 14 | `test_get_product_not_found` | 异常场景：查询不存在的商品返回空数据 | `/products/999999` | GET | ❌ 反向 | 🟡 NORMAL | 无 5xx 错误；**响应体为空**；`get_product_or_none()` 归一化为 `None` |

> **参数化**：编号 7~9 由 `test_get_product_detail` 展开（商品 ID `1/2/5`）；
> 编号 10~13 由 `test_get_products_by_category` 展开（4 个分类）。

---

## 四、购物车模块（4 条）

| # | 测试函数 | 用例名 | 接口 | 方法 | 类型 | 级别 | 核心断言 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | `test_get_cart[1]` | 查询购物车详情 | `/carts/1` | GET | ✅ 正向 | 🔴 BLOCKER | 状态码 200；字段完整；ID 一致；明细中 `productId > 0`、`quantity > 0`；**该用户的购物车列表中能找到它** |
| 16 | `test_get_cart[2]` | 查询购物车详情（参数化第 2 组） | `/carts/2` | GET | ✅ 正向 | 🔴 BLOCKER | 同上 |
| 17 | `test_add_to_cart` | 添加购物车：新增并回显商品明细 | `/carts` | POST | ✅ 正向 | 🔴 BLOCKER | 状态码 **201**（兼容 200）；回显 `userId` 与商品明细与请求一致；返回**新**购物车 ID 且不与已有重复；数量汇总正确 |
| 18 | `test_get_cart_not_found` | 异常场景：查询不存在的购物车返回空数据 | `/carts/999999` | GET | ❌ 反向 | 🟡 NORMAL | 无 5xx 错误；响应体为 `null`；`get_cart_or_none()` 返回 `None` |

> **参数化**：编号 15、16 由 `test_get_cart` 展开，`@pytest.mark.parametrize("cart_id", [1, 2])`。

---

## 五、函数与用例对应关系（11 个函数 → 18 条用例）

| 测试函数 | 参数化 | 展开用例数 | 对应用例编号 |
| --- | --- | --- | --- |
| `test_login_success` | — | 1 | 1 |
| `test_login_failed_with_wrong_password` | — | 1 | 2 |
| `test_login_failed_with_unknown_user` | — | 1 | 3 |
| `test_get_user` | `user_id` = 1, 2 | 2 | 4、5 |
| `test_get_all_products` | — | 1 | 6 |
| `test_get_product_detail` | `product_id` = 1, 2, 5 | 3 | 7、8、9 |
| `test_get_products_by_category` | `category` = 4 个分类 | 4 | 10、11、12、13 |
| `test_get_product_not_found` | — | 1 | 14 |
| `test_get_cart` | `cart_id` = 1, 2 | 2 | 15、16 |
| `test_add_to_cart` | — | 1 | 17 |
| `test_get_cart_not_found` | — | 1 | 18 |
| **合计 11 个函数** | | **18 条** | |

---

## 六、断言覆盖的 5 个层次

用例不只是"状态码 200 就算过"，断言覆盖了从浅到深的多个层次：

| 层次 | 检查内容 | 本项目示例 | 覆盖用例 |
| --- | --- | --- | --- |
| 1. 状态码 | 请求是否成功 | `assert response.status_code == 200` | 全部用例 |
| 2. 字段存在 | 该给的字段给了没 | `assert "token" in body`、`assert not missing` | 2、4、5、6~9、15、16 |
| 3. 值正确 | 数据是否一致 | `assert user["id"] == user_id`、`assert body["userId"] == user_id` | 1、4、5、7~9、15~17 |
| 4. 数据合理性 | 格式与取值是否合理 | `assert "@" in user["email"]`、`assert product["price"] > 0`、`assert image.startswith("http")` | 4~9、15、16 |
| 5. 业务逻辑与一致性 | 是否符合业务规则、接口间是否自洽 | `assert len(ids) == len(set(ids))`（商品 ID 唯一，仅用例 6）、`assert categories == {category}`（分类归属，用例 10~13）、`assert body["id"] not in existing_ids`（新 ID 未占用，用例 17）、商品详情与列表数据一致（用例 7~9）、购物车详情能在该用户购物车列表中找到（用例 15、16） | 6、7~9、10~13、15~17 |

---

## 七、两条用例的特别说明（评审常问）

**① 为什么编号 14、18 不写成「应返回 404」？**

实测发现该服务对不存在的资源**不返回 404**，而是返回 `200` + 空响应体（商品为完全空 body，购物车为 `null`）。
测试应当贴合**被测系统的真实契约**，而不是教科书规范。处理方式是：
**实测确认真实行为 → 按真实行为写断言 → 在 README 记录该契约**（见「服务端契约说明」）。

**② 为什么编号 17 不验证「创建后能查到」？**

Fake Store API 是模拟服务，`POST` 只返回创建结果、**不真正落库**。
若写成「创建 → 再查询验证存在」，该用例必然失败。因此断言收敛在创建动作的响应本身：
状态码、回显数据、新生成 ID、数量汇总。

---

## 八、如何只跑其中一部分

```bash
pytest                                  # 全部 18 条
pytest tests/test_user.py               # 只跑用户模块 5 条
pytest -m user                          # 按标记：用户模块
pytest -m product                       # 按标记：商品模块
pytest -m cart                          # 按标记：购物车模块
pytest -m smoke                         # 冒烟 3 条
pytest -k "login"                       # 按名字模糊匹配（跑所有含 login 的用例）
pytest tests/test_cart.py::TestCart::test_add_to_cart   # 精确跑某一条
```

查看用例清单（不执行）：

```bash
pytest --collect-only -q
```
