# 小程序、AI 与规则推荐

A 维护所有小程序代码，C 提供 AI/推荐接口，B/D 提供业务与基础能力。接口字段以 [接口文档](04-api-contracts.md) 为准。

## 1. 七个页面如何落地

| 页面 | 目录 | 主要操作 |
|---|---|---|
| 首页 | pages/home/ | 切换寻物/招领、搜索、筛选、分页 |
| 发布/编辑 | pages/publish/ | 手填、选图、AI、确认保存 |
| 我的 | pages/me/ | 昵称、我的发布、认领入口、退出 |
| 物品详情 | packages/post/detail/ | 查看、推荐、线索、申请 |
| 申请认领 | packages/claim/apply/ | proof、contact、postVersion |
| 申请列表 | packages/claim/list/ | sent/received 切换 |
| 申请详情 | packages/claim/detail/ | 核验、接受、拒绝、取消、归还 |

发布页有两种模式：无 id 时新建，有 id 时读取本人详情并编辑。编辑隐藏 type，保存带 expectedVersion。

我的页面直接分页显示我的发布；不另建“我的发布”页。三个主包 tabBar：首页、发布、我的。

app.json 的 pages 配置三个主包页面；subPackages 设 root=packages/post（页面 detail/index）和 root=packages/claim（页面 apply/index、list/index、detail/index）。tabBar 的 pagePath 必须对应主包 pages/.../index。每个路由的四个 index 文件由 A 一次建齐，不把页面拆给不同成员维护。

## 2. 详情页按钮

| 情况 | 显示什么 |
|---|---|
| 本人 OPEN LOST | 编辑、关闭、标记找回、查看线索、查看推荐 |
| 本人 OPEN FOUND 无活动申请 | 编辑、关闭、收到的申请、查看推荐 |
| 本人 OPEN FOUND 有待处理申请 | 关闭、收到的申请、查看推荐；不可编辑 |
| 本人 PROCESSING FOUND | 查看交接；不可普通关闭 |
| 他人 OPEN FOUND | 申请认领、举报 |
| 他人 OPEN LOST | 提供线索、举报 |
| 他人 PROCESSING | 只读公开资料、举报 |
| 本人历史/下架 | 查看状态与已有记录，不继续新业务 |

未登录看到公开资料，点击写操作再登录。本人操作按钮结合 isOwner、canEdit、canClaim 与状态展示，后端再次校验。

线索用详情页内表单或弹窗提交，不增加页面；本人查看线索也在同页分页展示。推荐只为本人 OPEN 信息加载，其他情况不调用推荐接口。

## 3. AI 表单流程

```text
输入文字 / 选择照片
    → 上传照片取得 fileId（可选）
    → 点击 AI 帮我填写
    → POST /ai/extract-features
    → 展示建议
    → 应用选定字段，继续修改
    → POST /posts 或 PUT /posts/{id}
```

只接一个支持中文和图片的模型。文字与图片共用接口，不训练模型，不建后台任务。

### C 的处理步骤

1. 校验文字长度、图片数量、当前用户与文件归属。
2. 从 D 获取固定类别/地点与校园当前日期。
3. 读取本人图片，以服务商支持的图片数据格式发送，不能传本机路径。
4. 模型返回 categoryCode、eventDate、color、brand、features、description。
5. 校验 JSON、类别编码、日期和长度。无法确认的字段置空。
6. 返回建议；格式不可用或超时返回 AI_UNAVAILABLE。

模型 key 只在后端。只发送本次物品输入，不发送账号 token、认领证明和交接方式。

### 等待与失败

后端超时初设 20 秒，客户端可设 25 秒，真实联调后调整。一次点击只发一次请求，不自动循环重试。

用户可以跳过并手填。输入改变时，旧响应不能自动覆盖；A 保存当前输入序号，收到过时响应只提示重新识别。

成功也必须点击应用建议，不自动发布。离开页面后不承诺恢复 AI 结果。

## 4. 初版规则：足够明确即可实现

C 通过 B 的 business/queries.py 读取候选，不直接调用他人的 repository 或 ORM 模型。推荐请求不调用模型、不写数据库。评分放 intelligence/rules.py，使用普通数据输入，可独立验证。

### 候选范围

- 源信息为本人、OPEN、visible。
- 候选为其他发布者、相反类型、OPEN、visible。
- 源类别不是 OTHER 时先取同类；是 OTHER 时允许所有类别。
- 按 createdAt、id 倒序最多取最近 100 条，课设阶段不做全库检索。

### 初始评分

| 条件 | 分数 | 说明 |
|---|---|---|
| 相同明确类别 | 40 | OTHER 与 OTHER 不加 |
| 颜色相同 | 20 | 去空白和大小写后比较，空值跳过 |
| 地点相同 | 20 | UNKNOWN/OTHER 不作为明确地点 |
| 日期合理接近 | 10 | 拾取不早于丢失，且相差不超过 3 天 |
| 外观/品牌短词命中 | 10 | 有任意一个长度至少 2 字的短词互相包含 |

短词从 features 和 brand 按逗号、顿号、空格分隔，不引入中文分词库。无词时跳过。

双方先各自规范空白、转小写，再比较短词；任意一对短词存在包含关系，该项只加一次 10 分。相同类别等其他项目也各加一次，总分不超过 100。

先规范成 LOST 和 FOUND 再比较日期，不能因源信息类型不同把前后算反。日期为空跳过，记忆不准导致早于时只不加分，不硬排除。

总分至少 40 才展示，最多 5 条。同分按日期差更小、再按发布时间与 ID 倒序。日期未知排在日期差已知之后。

这组分值是初始可调常量，用约 20 组样例检查；不是准确率承诺。

### 理由与误差

只返回实际加分依据，如“类别相同”“地点一致”。空字段不扣冲突分，但也不加证据分。分数仅排序，不展示为归属概率。

类别本身可能带来同款误推荐，仍需人工核验。没有达到阈值的结果返回 []。

语义匹配以后再加，不作为本版依赖。

## 5. 图片、表单与数据工具

| 组件或工具 | A 要处理的事情 |
|---|---|
| image-uploader | LOCAL/UPLOADING/UPLOADED/FAILED，单图失败重试 |
| feature-form | 新建/编辑共用，图片顺序、字典与空日期 |
| ai-suggestions | 单独保存建议，用户选择应用 |
| request | token、2xx/code、401/409、网络错误 |
| upload | wx.uploadFile，name=file，解析返回的字符串 data |

上传尚未结束时不提交。删除正在上传的图片要忽略其旧回调，不能又加回列表。

图片仅物品公开图，未绑定用本地预览。结束但未下架的图仍可访问，管理员下架或解绑后禁止公开读取，响应不缓存。

用户文字按普通文本展示，不渲染任意 HTML。

## 6. 微信与生命周期

wx.login 取得 code 后传后端，后端换微信身份并发平台 token。AppSecret 不放前端。不是自动获得手机号或学生认证。

onShow 刷新详情、申请和我的列表；onHide 不继续发请求。可保存文字草稿，临时图片失效时提示重选，不做复杂离线恢复。

D 配实际 AppID、HTTPS 和所需域名。真机验证登录、上传、图片、返回刷新，不能只看开发工具。

官方参考：[登录](https://developers.weixin.qq.com/miniprogram/dev/framework/open-ability/login.html)、[网络](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)。

## 7. 每页至少有的状态

加载、空数据、失败重试、未登录、无权限、状态变化；发布额外有上传中和 AI 失败，认领额外有 409 冲突和已被处理。

不要让用户通过反复点击来猜操作是否成功。
