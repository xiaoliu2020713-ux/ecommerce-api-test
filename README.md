# 电商系统接口自动化测试项目（ecommerce_api_test）

基于 **Python + Pytest + Requests + Allure** 搭建的接口自动化测试项目，测试对象为公开的
[Fake Store API](https://fakestoreapi.com/)，覆盖**用户登录、商品查询、购物车**三大核心模块。

项目采用「接口层封装 + 数据驱动 + 测试用例层」的分层设计：

- `api/` 负责接口封装与统一日志/报告埋点；
- `data/test_data.yaml` 负责测试数据与业务参数；
- `tests/` 只关注业务断言与用例组织，便于维护和扩展。

---

## 一、技术栈

| 分类 | 技术 / 工具 | 说明 |
| --- | --- | --- |
| 开发语言 | Python 3.8+ | 本项目在 Python 3.13 下验证通过 |
| 测试框架 | Pytest 7.4+ | 用例组织、fixture、参数化、标记 |
| HTTP 客户端 | Requests 2.31+ | 基于 `requests.Session` 会话复用 |
| 测试报告 | Allure 2.13+ | 步骤级记录、请求/响应附件、feature/story 分层 |
| 数据驱动 | PyYAML 6.0+ | YAML 管理测试数据 |
| 版本管理 | Git + GitHub | 代码托管 |

---

## 二、快速开始

### 1. 环境要求

- Python 3.8 及以上（推荐 3.10+）
- 可访问 `https://fakestoreapi.com` 的网络
- 查看 Allure 报告需要安装 [Allure 命令行工具](https://github.com/allure-framework/allure2/releases)（依赖 Java 8+）

### 2. 安装依赖

```bash
# 进入项目目录
cd ecommerce_api_test

# （推荐）创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 运行测试

```bash
# 运行全部用例（pytest.ini 中已配置 --alluredir=./reports/allure-results）
pytest

# 只运行某个模块
pytest tests/test_user.py
pytest tests/test_product.py
pytest tests/test_cart.py

# 按标记运行（user / product / cart / smoke）
pytest -m user

# 指定被测地址（默认 https://fakestoreapi.com）
pytest --base-url=https://fakestoreapi.com
# 或使用环境变量
API_BASE_URL=https://fakestoreapi.com pytest

# 生成 JUnit XML 报告
pytest --junitxml=reports/junit.xml
```

### 4. 查看 Allure 报告

```bash
# 方式一：直接启动本地服务并自动打开浏览器（推荐）
allure serve ./reports/allure-results

# 方式二：先静态生成，再打开 index.html（便于归档、分享）
allure generate ./reports/allure-results -o ./reports/allure-report --clean
allure open ./reports/allure-report
```

报告中可直接看到每个用例的 **Allure 步骤、完整请求报文、响应报文、状态码与耗时**。

---

## 三、覆盖接口列表

| 模块 | 接口 | 方法 | 用例 | 断言要点 |
| --- | --- | --- | --- | --- |
| 用户 | `/auth/login` | POST | `test_login_success` | 状态码 201、返回 JWT token |
| 用户 | `/auth/login` | POST | `test_login_failed_with_wrong_password` | 密码错误返回 401，且不返回 token |
| 用户 | `/auth/login` | POST | `test_login_failed_with_unknown_user` | 用户不存在返回 401 |
| 用户 | `/users/{id}` | GET | `test_get_user` | 状态码 200、用户 ID 一致、字段完整、邮箱格式合法 |
| 商品 | `/products` | GET | `test_get_all_products` | 状态码 200、共 20 条、字段完整、价格 > 0、ID 唯一 |
| 商品 | `/products/{id}` | GET | `test_get_product_detail` | 状态码 200、ID 一致、字段完整、与列表数据一致 |
| 商品 | `/products/category/{category}` | GET | `test_get_products_by_category` | 状态码 200、列表非空、分类归属正确 |
| 商品 | `/products/999999` | GET | `test_get_product_not_found` | 不存在的商品返回空数据（200 空响应体，非 404） |
| 购物车 | `/carts/{id}` | GET | `test_get_cart` | 状态码 200、ID 一致、明细结构合法、quantity > 0 |
| 购物车 | `/carts` | POST | `test_add_to_cart` | 状态码 201、回显 userId 与商品明细、返回新购物车 ID |
| 购物车 | `/carts/999999` | GET | `test_get_cart_not_found` | 不存在的购物车返回空数据（200 null，非 404） |

> **服务端契约说明（重要）**
> Fake Store API 是**模拟服务**，有两处与常规 REST 约定不同，用例已按真实行为设计断言：
> 1. 写操作（`POST /carts`）不会真正落库，只返回创建结果，
>    因此 `test_add_to_cart` 只对创建响应本身做断言，不校验后续 `GET` 的持久化结果；
> 2. 查询不存在的资源**不返回 404**，而是返回 **200 + 空响应体**（购物车为 `null`，商品为完全空 body），
>    因此异常用例断言「无 5xx 错误 + 响应体为空」，并通过 `get_product_or_none()` /
>    `get_cart_or_none()` 把空响应统一归一化为 `None`。

---

## 四、项目结构说明

```
ecommerce_api_test/
├── api/                        # 接口层：统一封装 HTTP 请求
│   ├── __init__.py             # 对外暴露 UserAPI / ProductAPI / CartAPI
│   ├── base_api.py             # BaseAPI：Session 管理、base_url 拼接、
│   │                           #   Allure 步骤与请求/响应附件、断言辅助
│   ├── user_api.py             # 用户模块：login() / get_user()
│   ├── product_api.py          # 商品模块：get_all_products() / get_product() /
│   │                           #   get_products_by_category()
│   └── cart_api.py             # 购物车模块：get_cart() / add_to_cart()
├── data/
│   └── test_data.yaml          # 测试数据：登录账号、商品 ID、分类、购物车数据
├── tests/                      # 用例层：只写业务断言
│   ├── __init__.py
│   ├── conftest.py             # session 级 fixture：user_api / product_api /
│   │                           #   cart_api / login_token、Allure 环境信息
│   ├── test_user.py            # 用户用例：登录成功、查询用户
│   ├── test_product.py         # 商品用例：列表、详情、分类查询
│   └── test_cart.py            # 购物车用例：查询、添加
├── reports/                    # 测试报告输出目录
│   ├── allure-results/         # Allure 原始结果（运行用例后生成）
│   └── allure-report/          # Allure HTML 报告（generate 后生成）
├── .github/workflows/
│   └── api-test.yml            # CI：提交后自动跑用例并发布 Allure 报告到 GitHub Pages
├── requirements.txt            # 依赖清单
├── pytest.ini                  # pytest 配置（addopts / testpaths / markers）
├── .gitignore
└── README.md
```

### 分层设计要点

1. **`BaseAPI` 统一收口**：`base_url` 拼接、超时、公共请求头、日志、Allure 附件全部在基类完成，
   业务子类只关心「请求哪个路径、传什么参数」。
2. **数据与代码分离**：账号、商品 ID、分类等易变数据放在 `test_data.yaml`，
   改数据不用改代码。
3. **fixture 会话复用**：`user_api` / `product_api` / `cart_api` 为 session 级，
   整个测试会话只建一次连接；`login_token` 登录一次即可复用。
4. **敏感信息脱敏**：日志与 Allure 附件中的 `password`、`token` 字段自动替换为 `***`。

---

## 五、测试用例设计

| 类型 | 说明 | 示例 |
| --- | --- | --- |
| 正向用例 | 校验正常业务链路 | 登录成功、商品列表、购物车详情 |
| 反向用例 | 校验异常处理 | 密码错误 401、资源不存在返回空数据 |
| 参数化用例 | 一份代码覆盖多组数据 | `test_get_user`（用户 1/2）、`test_get_product_detail`（商品 1/2/5）、`test_get_products_by_category`（4 个分类） |

标记（marker）说明：`user`（用户模块）、`product`（商品模块）、`cart`（购物车模块）、
`api`（自动为全部用例添加）。

---

## 六、常见问题

**Q1：用例报连接超时 / 无法访问？**
Fake Store API 是公网服务，请确认网络可访问 `https://fakestoreapi.com`；
也可通过 `--base-url` 指向自建的同款 Mock 服务。

**Q2：`allure` 命令不存在？**
需要单独安装 Allure 命令行工具（不是 `allure-pytest` 包）：
从 [Allure Releases](https://github.com/allure-framework/allure2/releases) 下载 zip，
解压后把 `bin` 目录加入 `PATH`，执行 `allure --version` 验证。

**Q3：`POST /carts` 后为什么查不到刚创建的数据？**
Fake Store API 为模拟服务，写接口不落库，这是预期行为，用例已按此设计断言范围。

**Q4：如何只跑冒烟用例？**
给关键用例加上 `@pytest.mark.smoke`，然后执行 `pytest -m smoke`。

---

## 七、持续集成（CI）

仓库内置 GitHub Actions 工作流 [`.github/workflows/api-test.yml`](.github/workflows/api-test.yml)：

- 触发时机：`push` / `pull_request` 到 `main`、`master`，以及手动触发（`workflow_dispatch`）；
- 执行内容：安装依赖 → 运行 `pytest` → 生成 Allure 报告；
- 结果输出：Allure 报告作为构建产物上传，并在 `push` 时自动发布到 GitHub Pages（`gh-pages` 分支）。

启用 GitHub Pages 后，可直接在线查看最新报告：
`https://<你的用户名>.github.io/ecommerce-api-test/`

本地等价命令：

```bash
pytest -m smoke                     # 只跑冒烟用例，快速验证核心链路
pytest --alluredir=./reports/allure-results
```

---

## 八、后续可扩展方向

- 增加接口 Schema 校验（`jsonschema`）与响应时间断言
- 引入 `pytest-xdist` 并行执行、`pytest-rerunfailures` 失败重试
- 增加数据库 / Redis 断言层，做数据一致性校验
- 接入通知渠道（企业微信 / 钉钉 / 飞书）推送构建结果

---

## 九、License

本项目仅用于学习与测试实践，测试对象为公开的 Fake Store API。
