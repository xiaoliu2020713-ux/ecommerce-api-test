# 电商系统接口自动化测试项目（ecommerce_api_test）

[![API Test](https://github.com/xiaoliu2020713-ux/ecommerce-api-test/actions/workflows/api-test.yml/badge.svg)](https://github.com/xiaoliu2020713-ux/ecommerce-api-test/actions/workflows/api-test.yml)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Pytest](https://img.shields.io/badge/Pytest-7.4%2B-0A9EDC)
![Allure](https://img.shields.io/badge/Report-Allure-orange)

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

### 5. 测试目标模式（真实 API / 本地 Mock）

```bash
pytest --api-mode=live     # 默认：访问真实 https://fakestoreapi.com
pytest --api-mode=mock     # 启动仓库内置的本地 Mock 服务，零外网依赖
pytest --api-mode=auto     # 先探测真实接口，被拦截/不可达时自动降级为 Mock
# 等价环境变量写法
API_MODE=mock pytest
```

| 模式 | 被测对象 | 适用场景 |
| --- | --- | --- |
| `live` | `https://fakestoreapi.com` | 本地开发、验证真实接口契约（默认） |
| `mock` | 本地 `sandbox/mock_server.py` | 云 CI、内网、无外网环境，执行稳定且秒级完成 |
| `auto` | 优先真实，必要时降级 | 本地或 CI 通用，兼顾真实性与稳定性 |

> **为什么需要 Mock？**
> GitHub Actions 等云 CI 运行在数据中心 IP 上，访问 `https://fakestoreapi.com`
> 会被 Cloudflare 机器人防护拦截，返回 `403` + "Just a moment..." 挑战页，
> 属于**运行环境限制，而不是用例缺陷**。
> 为让 CI 稳定可信，工作流主任务使用 `--api-mode=mock` 执行**同一套用例**
> （共用同一份 `api/` 封装与全部断言），另有一个非阻塞任务用 `--api-mode=live`
> 探测线上接口可达性。

Mock 服务完全用标准库实现，无需额外依赖，可单独启动用于手工联调：

```bash
python sandbox/mock_server.py --port 8765
# 然后另开一个终端
pytest --base-url=http://127.0.0.1:8765
```

它复刻了线上接口的行为契约，包括两处「非常规」约定：不存在的商品返回 `200` + 空响应体、
不存在的购物车返回 `200` + `null`（均不是 404）。

---

## 三、覆盖接口列表

> 本表为**接口维度**的覆盖情况（用例列按测试函数名展示）。
> 全部 **18 条用例**的逐条清单（含参数化取值、优先级、断言要点）见 **[TESTCASES.md](TESTCASES.md)**。

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
├── sandbox/
│   └── mock_server.py          # 本地 Mock 服务（标准库实现，供 CI 稳定执行）
├── .github/workflows/
│   └── api-test.yml            # CI：跑用例（mock 门禁 + live 探测）并发布 Allure 报告
├── requirements.txt            # 依赖清单
├── pytest.ini                  # pytest 配置（addopts / testpaths / markers）
├── TESTCASES.md                # 全部 18 条测试用例清单（含参数化取值与断言要点）
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
5. **测试目标可切换**：`--api-mode` 让同一套用例既能打真实 API，也能打本地 Mock，
   CI 与本地不会因为外网策略产生结果差异。

---

## 五、测试用例概览

> 📋 **全部 18 条用例的逐条清单见 [TESTCASES.md](TESTCASES.md)**
> （含参数化取值、优先级、断言要点、函数与用例对应关系、如何只跑某一部分）

**用例总数：18 条**（由 11 个测试函数经参数化展开）

| 模块 | 测试文件 | 用例数 |
| --- | --- | --- |
| 用户模块 | `tests/test_user.py` | 5 |
| 商品模块 | `tests/test_product.py` | 9 |
| 购物车模块 | `tests/test_cart.py` | 4 |
| **合计** | | **18** |

### 按测试类型（怎么测）

| 类型 | 数量 | 说明 | 对应用例 |
| --- | --- | --- | --- |
| ✅ 正向用例 | **14** | 正常业务流程，期望调用成功 | #1, #4-13, #15-17 |
| ❌ 反向用例 | **4** | 故意制造异常，期望被正确拒绝 | 编号 2、3、14、18 |

### 按优先级（先测谁）

| 优先级 | 数量 | 含义 | 对应用例 |
| --- | --- | --- | --- |
| 🔴 BLOCKER 阻塞级 | **5** | 挂了核心链路就走不通，必须最先修 | 登录、商品列表、购物车查询×2、加购物车 |
| 🟠 CRITICAL 严重级 | **10** | 核心功能，挂了要尽快修 | 密码错误、查用户×2、商品详情×3、分类查询×4 |
| 🟡 NORMAL 一般级 | **3** | 边界与异常分支，优先级相对较低 | 用户不存在、商品不存在、购物车不存在 |

> 用例编号与「维度」的对应关系详见 [TESTCASES.md](TESTCASES.md) 第一节总览。

### 冒烟用例（快速体检）

从 18 条中挑出 3 条最关键、最快的主干用例，改完代码先用它做快速回归：

| 冒烟用例 | 覆盖环节 | 运行方式 |
| --- | --- | --- |
| 登录成功、商品列表、加入购物车 | 登录 → 浏览商品 → 下单 | `pytest -m smoke` |

### 其余测试设计手法

| 手法 | 说明 | 示例 |
| --- | --- | --- |
| 参数化 | 一份代码覆盖多组数据 | `test_get_user`（用户 1/2）、`test_get_product_detail`（商品 1/2/5）、`test_get_products_by_category`（4 个分类）、`test_get_cart`（购物车 1/2） |
| 接口间一致性 | 交叉校验两个接口的数据是否自洽 | 商品详情与商品列表数据一致；购物车详情能在「该用户的购物车列表」中找到 |
| 业务规则校验 | 校验数据是否满足业务约束 | 价格 > 0、商品 ID 不重复、分类归属正确、新建购物车 ID 未占用 |

**标记（marker）说明**：`user`（用户模块）、`product`（商品模块）、`cart`（购物车模块）、
`smoke`（冒烟）、`api`（自动为全部用例添加）。

**常用运行方式**

```bash
pytest                      # 全部 18 条
pytest -m user              # 只跑用户模块
pytest -m smoke             # 只跑冒烟 3 条
pytest -k "login"           # 按名字模糊匹配
pytest --collect-only -q    # 只列出用例清单，不执行
```

---

## 六、常见问题

**Q1：用例报连接超时 / 无法访问？**
Fake Store API 是公网服务，请确认网络可访问 `https://fakestoreapi.com`。
若在云 CI、内网或代理环境下被 Cloudflare 拦截（返回 `403` + "Just a moment..."），
请改用本地 Mock：`pytest --api-mode=mock`，或用 `--api-mode=auto` 自动降级。

**Q2：`allure` 命令不存在？**
需要单独安装 Allure 命令行工具（不是 `allure-pytest` 包）：
从 [Allure Releases](https://github.com/allure-framework/allure2/releases) 下载 zip，
解压后把 `bin` 目录加入 `PATH`，执行 `allure --version` 验证。

**Q3：`POST /carts` 后为什么查不到刚创建的数据？**
Fake Store API 为模拟服务，写接口不落库，这是预期行为，用例已按此设计断言范围。

**Q4：如何只跑冒烟用例？**
给关键用例加上 `@pytest.mark.smoke`，然后执行 `pytest -m smoke`。

**Q5：为什么 CI 用 Mock 而本地用真实接口？**
GitHub Actions 的数据中心 IP 会被 fakestoreapi 的 Cloudflare 防护拦截（403 挑战页），
若 CI 直接跑 `live`，失败原因是环境而非代码。因此 CI 门禁使用 `--api-mode=mock`
保证结果稳定可复现，同时保留 `live` 探测任务如实反映线上接口当时的可达性。

---

## 七、持续集成（CI）

仓库内置 GitHub Actions 工作流 [`.github/workflows/api-test.yml`](.github/workflows/api-test.yml)：

| 任务 | 内容 | 是否阻塞 CI |
| --- | --- | --- |
| `api-test`（主任务） | `pytest --api-mode=mock` 跑全部 18 条用例 → 生成 Allure 报告 → 上传产物 → 发布 GitHub Pages | 是（CI 门禁） |
| `real-api-check`（辅助任务） | `pytest --api-mode=live` 探测线上 Fake Store API 真实可达性，结果作为产物留存 | 否（`continue-on-error`） |

- 触发时机：`push` / `pull_request` 到 `main`、`master`，以及手动触发（`workflow_dispatch`）；
- 报告发布：`push` 到 `main` 时自动发布到 `gh-pages` 分支，开启 Pages 后可在线查看。

**在线查看最新 Allure 报告（本仓库已开启 Pages）：**

<https://xiaoliu2020713-ux.github.io/ecommerce-api-test/>

> 说明：Pages 会自动把站点根路径重定向到最新的构建目录（如 `/4/index.html`），
> 直接访问上面的地址即可；每次构建保留最近 20 次报告，历史趋势在图表的 Trend 中查看。

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
