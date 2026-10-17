# 开发顺序、交接与验收

保持六张表、七页、32 个接口，不以补文档为由增加第一版功能。

## 1. 开发前先完成共同骨架

先由 D 汇总、B/C 配合交付一个共同起点，不能四个人分别建工程后再拼接。

| 必备项 | 负责人 | 完成标准 |
|---|---|---|
| Python 工程和依赖 | D | 同一 Python 3.12 环境可安装；main.py 能启动 |
| 公共类型和异常 | D | CurrentUser、成功/错误信封、400 校验、camelCase 与 ID 输出可演示 |
| 六表及 ORM | B/D | schema.sql 可建库；两个 models 模块注册到同一个 Base |
| 内部函数签名 | B/C/D | 下文函数的参数、返回类型建立为实际 Python 定义，不再各自猜测 |
| 小程序起始工程 | A | 七页路由和三入口可打开，公共请求/模拟开关能用 |
| 管理端起始工程 | D | Vue 能启动并配置 API 地址 |

基础出口：从小程序请求一次后端公开列表，看到统一 JSON；从 /docs 能查看已注册接口。未完成接口明确标记未实现，不用空数组或假成功掩盖。该阶段不要求所有业务齐全。

### 后续四步开发

| 阶段 | 主要工作 | 出口条件 |
|---|---|---|
| 1 基础 | D 工程/登录/上传，A 页面，B/C 示例 | 真机、真实模型能调用 |
| 2 业务 | B 发布到归还，A 联调，D 基础后台 | 无 AI 可走完业务 |
| 3 特色 | C 提取/推荐，A 接表单与详情 | 无图可推荐，图片有建议 |
| 4 交付 | 四人回归、修错、报告、演示 | 关键用例通过，有证据 |

先做真实模型最小调用，避免最后才发现网络或配额不可用。D 先给公共能力，不代写 B/C 业务。

## 2. 第一批可分配任务

| 人员 | 首批任务 | 交付给谁 |
|---|---|---|
| A | 三入口、七页路由、表单、公共请求和固定示例 | B/C/D 反馈缺少字段 |
| B | 三张业务表草稿、信息与申请 API 示例、状态规则 | A 联调，C 查询合同，D 下架合同 |
| C | 模型最小调用、提取示例、规则函数 | A 接界面，B 确认查询字段 |
| D | 后端工程、平台表、登录上传、字典 | A/B/C |

必须先确认：成员姓名、截止日期、AppID、数据库与工具版本、模型和额度、服务器地址。暂不编造具体工期。

相对投入可按“共同骨架 15%、业务闭环 40%、AI/推荐与后台 25%、验收报告 20%”安排，这是讨论进度的初始比例，不是固定天数。提前验证模型；基础流程不因 AI 联调失败而停工。

## 3. Python 内部对接

统一用普通 Python 函数，不强制每个文件包装一个 Service 类。函数必须带类型标注。内部 ID 为 int，HTTP ID 序列化为字符串。

### 固定函数与所有者

| 提供者/文件 | 函数及结果 |
|---|---|
| B business/queries.py | get_post(session, post_id) → PostReadModel，不存在抛 404 |
| B business/queries.py | find_candidates(session, source, limit=100) → list[PostReadModel] |
| D platform/services/files.py | bind_to_post(session, actor_id, post_id, ordered_file_ids) → None |
| D platform/services/files.py | read_owned_images(session, actor_id, file_ids) → list[OwnedImage] |
| D platform/services/files.py | get_public_images(session, post_id) → list[ImageView] |
| D platform/services/users.py | get_public_profiles(session, user_ids) → dict[int, UserBrief] |
| D platform/services/dictionaries.py | get_categories()/get_locations() → 字典列表；campus_today() → date |
| B business/services/posts.py | hide_post(session, admin_id, post_id, reason) → PostStateResult |
| D platform/dependencies.py | optional_user → CurrentUser 或 None；require_user/require_admin → CurrentUser |

PostReadModel 由 B 放 business/schemas.py：id、owner_id、type、title、category_code、location_code、event_date、color、brand、features、status、visible、version、created_at。它是内部只读值，不是可直接公开的 HTTP DTO。

OwnedImage/ImageView/UserBrief 由 D 放 platform/schemas.py。OwnedImage 包含 bytes/MIME；ImageView 包含 file_id/url；UserBrief 只有 id/nickname。PostStateResult 由 B 定义，包含 id/status/visible/version。CurrentUser 放 common/auth.py，包含 id/nickname/role，不含 token 原值。

get_post 不负责当前业务的权限判定，C/D 拿到结果后按场景检查。find_candidates 在查询中限制相反类型、其他发布者、OPEN、visible、类别范围，最近最多 100 条。B 的 queries 不导入文件或写服务，避免循环导入。

bind_to_post 必须使用调用方 Session，替换整组关联，最多三个不同 ID，校验本人及未被其他帖占用。get_public_images 非公开返回 []。read_owned_images 对越权返回 403，不能用公开下载 URL 绕过本人检查。

### 一次写操作的事务

```python
# 约定示意，尚未实现；actor 来自独立短会话认证。
def accept_claim_endpoint(body, actor, session):
    with session.begin():
        result = accept_claim(session, actor.id, body)
    return success(result)
```

路由负责 begin/提交/回滚，service/repository 不提交，只做查询、修改和必要的 flush。传入的业务 Session 在 begin 前不得执行查询；认证使用独立短 Session，防止隐式事务已开启。

accept_claim 等内部函数先锁 post，再读并检查 claim；跨 B/D 图片关联也共享此事务。发布先 flush 获得 post.id，再绑定图片，一次提交。文件物理上传先于正式发布，不声称磁盘和 MySQL 可用同一个数据库事务回滚。

AI 路由在短 Session 内读取图片元数据/物品信息，再关闭 Session 后调用模型。仅传普通数据，不将 ORM 实体带入模型请求；图片不得在网络等待时占用数据库锁。

### 并行开发的替身

A 用与接口一致的固定 JSON；C 用 PostReadModel 样例和模拟模型响应。测试可替换依赖，开发环境外部服务未接通时必须明确提示，不把替身混入演示成功记录。

每个模块先交一组成功/失败输入输出，再写实现。公共返回结构归 D，状态与私密字段归 B，AI 和评分归 C；变更先同步接口文档与调用方。

## 4. 核心验收

| 编号 | 场景 | 预期 | 主责 |
|---|---|---|---|
| T01 | 无照片、无 AI 发布 | 保存并可搜索 | A/B |
| T02 | 文字与图片提取 | 可修改，确认后才发布 | A/C |
| T03 | 模型超时/格式错误 | 保留表单，可手填 | A/C |
| T04 | 未登录或改别人信息 | 后端拒绝 | B/D |
| T05 | 重复申请同一招领 | 不新增活动申请 | B |
| T06 | 两份申请并发接受 | 最多一份 ACCEPTED | B |
| T07 | 取消、完成及重复动作 | 状态正确，终态 409，不复活 | B |
| T08 | 有活动申请时编辑 | 禁止；旧详情创建申请 409 | B |
| T09 | 他人/管理员读私密证明 | 不因角色额外开放，列表无正文 | B/D |
| T10 | 下架交接中的信息 | 申请结束、物品图不公开 | B/D |
| T11 | 无图失主推荐 | 合理候选或 [] | C |
| T12 | 退出、登录、返回页面 | 刷新状态，不误操作 | A/D |
| T13 | 举报处理 | 管理员查看、下架、填写结果 | D |
| T14 | 长度、未来日期、非法字典 | 400，前后端约束一致 | A/B/D |
| T15 | 过大、伪格式、他人图片 | 拒绝，不能抢占关联 | D |
| T16 | 已有活动申请后用旧版本重提 | 先返回已有记录，不误报版本 | B |
| T17 | OTHER/UNKNOWN、空日期、同分 | 不虚加分，排序稳定 | C |
| T18 | 新登录后旧 token 退出 | 不能清除新登录态 | D |

这是待执行计划，不能记作已通过。并发用实际 MySQL，不能只验证前端禁用按钮。

## 5. 几个需要重点复现的步骤

### 并发接受

准备同一 FOUND 的两份 PENDING，同时调用 accept。预期一个 200、一个 409；数据库只有一条 ACCEPTED，post=PROCESSING。

### 取消后重试其他人

取消已接受的申请，确认 post=OPEN。其他 PENDING 仍可被接受，旧 CANCELLED 不能重开。

### 图片和下架

先访问已发布物品图，再下架，重新请求相同地址应 404。普通信息历史不能借管理角色读 proof。

### AI 提取

文字、图片、二者都有分别调用；模糊品牌应为空。等待时手动修改表单，旧响应不能自动覆盖。

## 6. 简单 AI 样例

准备约 20 组虚构或授权样例：无图、模糊图、同款不同物、未知地点日期、无正确候选。

记录输入、期望、实际、是否合理、大致耗时。暂不要求复杂指标或评测流水线，不编造成功率。

## 7. 文档与环境检查

从项目根目录运行：

```text
node scripts/check-docs.mjs
```

检查当前链接、JSON、重复接口、目录、状态清单和用例；archive 不参与。此命令不会启动微信、MySQL 或模型。

D 统一 requirements 和环境配置；B/D 提交建表脚本，D 合并。共用一个 SQLAlchemy Engine/Session 工厂，图片放持久化目录。

工程实现后，从 backend 目录使用 python -m pytest；先跑本模块，再跑全套。Python 环境、数据库初始化、管理员脚本与目标启动命令见 [后端说明](../backend/README.md)。目前这些是待交付项，不能据此声称命令已经可执行。

合并门槛：应用能启动、路由无重复、现有测试通过、API 字段与文档一致。先接通“登录→无图发布→列表→详情”，再加图片、认领、线索、AI 和推荐，不等各自全部做完才合并。

## 8. 答辩与报告

用固定样例演示：寻物 → 招领 → AI 建议 → 推荐 → 认领 → 归还 → 手动结束寻物。

报告至少对应需求、分层架构、六表关系、接口、页面与测试记录。重点讲 AI 辅助、明确分工、事务和权限，扩展功能只写后续计划。
