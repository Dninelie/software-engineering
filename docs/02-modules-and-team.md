# 四人分工与 Python 文件

目标是各自维护明确的文件，在一个 FastAPI 工程内协作。文件清单是待实现计划，不代表这些文件已经存在。

## 1. 总览与独立性

| 成员 | 独占维护范围 | 依赖 | 可先独立完成 |
|---|---|---|---|
| A | miniprogram/ | B/C/D 的 HTTP API | 页面、组件、模拟数据 |
| B | backend/app/business/ | D 身份、文件、字典 | 状态规则、业务查询、业务表 |
| C | backend/app/intelligence/ | B 只读查询、D 本人图片 | 评分函数、模型调用、AI 样例 |
| D | backend/app/platform/、common/、main.py、admin-web/、deploy/ | B 下架与只读查询 | 基础工程、身份、上传、管理页 |

B/D 各有三张表。C 不建表。A 不写 Python，B/C/D 不拆写小程序页面。

独立性是“不同文件可以并行”，并不意味着四部分能各自作为完整应用启动。后端共用一个进程、一个依赖文件、一套数据库。

## 2. A：微信小程序

下列路径均位于 miniprogram/。

| 目录 | 内容 |
|---|---|
| pages/home/ | 寻物/招领列表、搜索、筛选、分页 |
| pages/publish/ | 新建/编辑、物品图、AI 建议确认 |
| pages/me/ | 昵称、我的发布、申请入口、退出 |
| packages/post/detail/ | 信息、推荐、线索、申请入口 |
| packages/claim/apply/ | 文字证明和交接方式 |
| packages/claim/list/ | 发出/收到的申请 |
| packages/claim/detail/ | 核验、接受、拒绝、取消、归还 |
| components/ | post-card、feature-form、image-uploader、ai-suggestions、match-list |
| services/business/、intelligence/、platform/ | 对应三组 HTTP 接口，全部归 A |
| utils/、config/ | 请求、登录、上传、环境 |

每页 index.ts、index.wxml、index.wxss、index.json。app.json、app.ts、项目配置统一归 A，不按后端负责人拆页。

先用固定 JSON 做页面，再切换真实 API；模拟开关仅限开发环境，不能用模拟数据冒充联调通过。

## 3. B：业务模块

以下路径相对 backend/app/。

| 拟建文件 | 职责 |
|---|---|
| business/routers/posts.py | 发布、编辑、查询、关闭、标记找回 |
| business/routers/claims.py | 申请、查询、接受、拒绝、取消、归还 |
| business/routers/clues.py | 提交/查看文字线索 |
| business/services/posts.py | 信息规则、图片关联、管理员下架 |
| business/services/claims.py | 认领状态、同帖锁、交接 |
| business/services/clues.py | 线索权限 |
| business/queries.py | 给 C/D 的只读数据出口 |
| business/repositories.py | post/claim/clue 数据访问与行锁 |
| business/models.py | 三张业务表的 SQLAlchemy 映射 |
| business/schemas.py | 业务输入、公开响应、PostReadModel |
| tests/business/（位于 backend 下） | 状态、权限和 MySQL 事务测试 |

B 一起维护 post、claim、clue，避免归还事务分给两个人。向 D 交业务表 SQL，向 C/D 交查询函数和类型，向 A 交接口示例。

B 不读写 app_user/file_asset/report 的 ORM 模型，跨模块通过约定的函数协作。需要昵称等资料时使用 D 的批量用户资料函数，不把证明或联系方式混入公开响应。

## 4. C：AI 与匹配模块

| 拟建文件 | 职责 |
|---|---|
| intelligence/routers/ai.py | 图文提取 API |
| intelligence/routers/matches.py | 推荐 API |
| intelligence/services/extract.py | 参数、图片、模型结果校验 |
| intelligence/services/matching.py | 获取候选、调用评分、组合推荐 |
| intelligence/provider.py | 一个模型供应商的 HTTP 请求和结果解析 |
| intelligence/rules.py | 纯函数：特征归一化、评分、理由、排序 |
| intelligence/schemas.py | 提取请求/建议、推荐响应 |
| tests/intelligence/（位于 backend 下） | 规则样例、模型失败和解析测试 |

C 不建 ORM 表、不保存匹配结果、不访问其他人的 repository。provider.py 先写一个具体服务商实现，暂不建多供应商插件体系。

C 维护 tests/ai-samples/ 的约 20 组样例。前期用 PostReadModel 固定数据测试规则，不必等待 B 全部接口完成。

## 5. D：平台、后台与基础工程

| 拟建文件 | 职责 |
|---|---|
| platform/routers/auth.py | 微信/管理员登录、退出、个人资料 |
| platform/routers/files.py | 上传和公开图片内容 |
| platform/routers/dictionaries.py | 类别、地点 |
| platform/routers/reports.py | 举报、举报管理和处理 |
| platform/routers/admin.py | 信息管理；下架调用 B 的 posts 服务 |
| platform/services/auth.py | 微信换身份、随机 token、管理员密码 |
| platform/services/users.py | 批量查用户公开资料，只返回 id/nickname |
| platform/services/files.py | 校验、保存、关联、读取图片 |
| platform/services/dictionaries.py | 固定字典和校园日期 |
| platform/services/reports.py | 举报查询与处理 |
| platform/repositories.py | app_user/file_asset/report 数据访问 |
| platform/models.py、schemas.py | 三张平台表、平台输入输出 |
| platform/dependencies.py | optional_user、require_user、require_admin |
| common/config.py、database.py | 环境配置、Engine/Session/Base |
| common/schemas.py、errors.py | 返回信封、字段别名、业务异常及处理 |
| common/auth.py | CurrentUser 普通数据类型，不解析 token |
| main.py | 初始化、异常注册、统一挂载路由、管理端跨域 |
| tests/platform/（位于 backend 下） | 身份、文件、举报 |
| admin-web/、deploy/ | 三页后台、部署与环境 |

D 管理 backend/requirements.txt、requirements-dev.txt、.env.example，合并 schema.sql，确认模型已被导入并加入同一 Base.metadata。其他人提出依赖，由 D 统一加入，不各自新建后端工程。

D 前期先完成公共骨架、身份、上传、字典；三页后台在基础链路接通后再做，避免成为所有人的等待点。

## 6. 跨模块规则

- B 的 posts 服务调用 D 的文件绑定，传同一个 Session，原子提交。
- D 的 files 服务可调用 B 的 queries，只读检查可见性，不调 posts 写服务。
- C 只使用 B 的 queries、D 的文件/字典函数。
- D 的 admin 路由调用 B 的 hide_post，不自己改 claim。
- B 的查询层不导入文件服务；路由不被 service 导入；main.py 只作为装配入口。
- 不互相导入 models 后随意改别人表；不在公共目录堆业务代码。
- ORM 实体不直接作为 HTTP 响应；分别定义公开信息和私密申请响应。

准确的函数输入、返回和事务边界见 [开发交接](06-development-and-testing.md)。HTTP 以 [接口](04-api-contracts.md) 为准。

## 7. 身份和公共文件

FastAPI 在每个路由明确绑定身份依赖：普通写接口 require_user，管理接口 require_admin；公开列表、详情、字典和图片按其约定检查。

两个登录入口不要求身份。GET /posts/{id} 可 optional_user，用于本人/管理员历史权限；未登录不能读取非公开历史。知道文件 ID 不能跳过文件关联/可见性检查。

Python 用 snake_case，JSON 保持 camelCase。D 给公共 schema 基类和异常处理，B/C 使用同一套；错误字段、默认值、ID 类型不得各自发挥。

## 8. 交付与合并

| 人员 | 至少交付 |
|---|---|
| A | 页面、接口调用、真机记录 |
| B | 业务代码、三表 SQL、状态/并发证据 |
| C | 提取与推荐、评分样例、AI 失败演示 |
| D | 公共工程、平台与后台、三表 SQL、启动和部署说明 |

B/D 先各交建表片段，再由 D 合并 backend/sql/schema.sql，避免同时改一个脚本。公共文件归 D；业务文件各归作者。每个小功能完成即合并并验证，不等所有模块写完。

该分工维持低文件冲突，但 A/B/D 工作较集中。C 可协助整理联调样例和验收记录；若转交功能，要连同完整文件和维护责任一起转交，不能两人同时改同一模块。
