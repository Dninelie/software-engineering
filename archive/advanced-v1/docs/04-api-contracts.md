# 接口说明

用于前后端联调。所有路径默认加 `/api/v1`，当前均为待实现的约定。机器可读字段与响应定义见 [OpenAPI](contracts/openapi.json)，审查结论见 [设计审查](13-design-review.md)。

**查阅顺序：**先读通用规则，再查自己负责的接口组。业务状态见 [需求规格](01-requirements.md)，表字段见 [数据库设计](03-database.md)。

## 接口负责人

| 提供者 | 接口范围 | 小程序调用代码 |
|---|---|---|
| B | 信息、线索、认领、通知 | A：services/business/ |
| C | AI、任务查询、匹配 | A：services/intelligence/ |
| D | 登录、文件、字典、举报、管理 | A：services/platform/；D：管理端 services |

A 维护所有小程序请求代码。后端负责人提供 DTO、权限和示例。共同确认合同后再改字段；本次调整不改变原有 API 路径。

## 1. 通用规则

### 1.1 请求格式

| 项目 | 约定 |
|---|---|
| 普通请求 | UTF-8 JSON，字段用 camelCase |
| 文件上传 | multipart，单独处理 |
| 业务 ID | 字符串 |
| 时间点 | 带时区的 ISO 8601 |
| 登录身份 | `Authorization: Bearer <token>` |
| 创建防重复 | `clientRequestId` |
| 编辑防覆盖 | `expectedVersion`，对应 rowVersion |

身份从 token 取得，不信任客户端传入的 ownerId。

相同 clientRequestId 和相同内容返回已有结果；相同键却内容不同，返回幂等冲突。token 到期后重新微信登录，本版不另设刷新令牌流程。

### 1.2 返回格式

```json
{
  "code": "OK",
  "message": "操作成功",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "pageSize": 20
  },
  "requestId": "r1001"
}
```

列表规则：

- page 从 1 开始，pageSize 默认 20、最大 50。
- 默认按 createdAt、id 倒序稳定排序。
- 没有数据返回空数组，不返回 null。
- 文件内容返回二进制，不套上述 JSON。

### 1.3 HTTP 状态码

| 状态码 | 含义 |
|---|---|
| 200 | 查询或修改成功 |
| 201 | 创建资源成功 |
| 202 | 已接受后台任务 |
| 400 | 参数错误 |
| 401 / 403 | 未登录 / 无权限 |
| 404 | 对象不存在或不允许查看 |
| 409 | 状态、版本或幂等冲突 |
| 413 | 文件过大 |
| 415 | 文件类型不支持 |
| 429 | 请求过频或额度限制 |
| 503 | 服务暂不可用 |

私密对象越权可以统一返回 404，内部原因留在日志中。

### 1.4 错误示例

HTTP 409：

```json
{
  "code": "POST_VERSION_CONFLICT",
  "message": "信息已更新，请刷新后重试",
  "data": null,
  "requestId": "r1001"
}
```

前端根据 code 判断行为，不解析 message 文案。

## 2. 登录、资料与字典（D）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/auth/wechat-login` | 用微信 code 换平台 token |
| POST | `/auth/logout` | 撤销当前会话，重复调用返回成功 |
| GET | `/me` | 获取本人资料 |
| PATCH | `/me` | 修改 nickname、avatarFileId |
| GET | `/categories` | 启用分类 |
| GET | `/locations` | 启用地点 |

微信登录和字典可公开调用，资料与退出接口需要当前登录态。退出接口允许对已撤销的同一凭证返回幂等成功。

登录输出：

| 字段 | 说明 |
|---|---|
| token | 平台随机登录凭证 |
| expiresAt | 到期时间 |
| user | id、nickname、avatarUrl、role、status |

openid、session_key 不作为平台 token。账号受限后，所有写接口都必须拒绝操作。

## 3. 文件（D）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/files` | 登录后上传 |
| GET | `/files/{id}/content` | 读取公开图片或持有效许可的私密图片 |
| POST | `/files/{id}/access-grants` | 校验权限后取得短期地址 |

### 上传请求

multipart 字段为 file、purpose。返回：

| 字段 | 说明 |
|---|---|
| fileId | 后续提交业务时引用 |
| purpose | 文件用途 |
| mimeType | 类型 |
| byteSize | 大小 |

用途为 POST_IMAGE、CLUE_IMAGE、CLAIM_PROOF、AVATAR。用途不是公开权限，未发布文件默认不公开。

第一版接收 JPEG、PNG，服务端校验实际格式；不支持的格式返回 FILE_TYPE_UNSUPPORTED。图片内容使用真实 image/jpeg 或 image/png 响应头。

### 私密图片展示

```text
携带 token 请求访问许可 → 返回 url、expiresAt → 小程序展示图片
```

不能把平台 token 拼在图片地址上。证明读取权限由相关业务判断，不能只凭 fileId。

短期地址使用 fileId、签发主体、用途、expires、nonce 与签名校验。每次读取仍检查文件关联、账号和业务可见性，避免下架后旧地址继续公开。返回 Cache-Control: no-store；签名有效期默认 60 秒。签名地址仍是可转发的短期凭证，不能防截图。

## 4. 信息发布与查询（B）

### 4.1 接口列表

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/posts` | 登录后发布，返回 201 |
| GET | `/posts` | 公开列表与筛选 |
| GET | `/posts/{id}` | 公开详情或本人历史 |
| PUT | `/posts/{id}` | 本人编辑完整可编辑内容 |
| GET | `/me/posts` | 本人的全部状态信息 |

编辑要求本人、可见、OPEN，并提交 expectedVersion。type、ownerId 不可编辑；完整 PUT 仅包含可编辑字段，未知字段拒绝。

LOST 若已有 ACCEPTED 关联申请，也暂不可编辑、关闭或手动解决，需先处理交接。

公开详情仅用于 VISIBLE 且 OPEN/PROCESSING；已关闭、解决或下架的信息不因知道 ID 就公开。本人历史与申请中的最小物品摘要分开返回。

公共筛选参数：

| 参数 | 作用 |
|---|---|
| type、keyword | 信息类型、关键词 |
| categoryId、locationId | 分类、校园地点 |
| startDate、endDate | 日期范围 |
| page、pageSize | 分页 |

未知时间不命中日期筛选；未设置日期筛选时可正常展示。公共列表不接受任意 status 绕过可见规则。

### 4.2 发布请求示例

```json
{
  "clientRequestId": "c91cf19c-0695-4e67-9af1-7f85ca806d90",
  "type": "LOST",
  "title": "寻找黑色保温杯",
  "categoryId": "12",
  "locationId": "25",
  "timePrecision": "PERIOD",
  "eventDate": "2026-10-15",
  "timePeriod": "AFTERNOON",
  "eventAt": null,
  "description": "黑色杯身，银色杯盖，在食堂附近遗失。",
  "features": {
    "color": "黑色",
    "brand": null,
    "appearance": ["银色杯盖"]
  },
  "imageIds": []
}
```

时间字段组合见 [需求中的时间精度](01-requirements.md)。locationId=null 表示地点未知；正式发布不要求存在 AI 草稿。

创建和编辑响应 data 包含 id、rowVersion、contentVersion、matchJobId。EXACT 请求只填 eventAt；服务端派生校园 eventDate 供日期筛选。

### 4.3 列表和详情返回什么

| 数据结构 | 字段 |
|---|---|
| PostCard：身份 | id、type、title |
| PostCard：分类地点 | categoryName、locationName |
| PostCard：时间 | timePrecision、eventDate、timePeriod、eventAt |
| PostCard：展示状态 | thumbnailUrl、status、createdAt |
| PostDetail：补充内容 | categoryId、locationId、description、features、images |
| PostDetail：版本 | contentVersion、rowVersion |
| PostDetail：交互 | 有限发布者信息、allowedActions |

allowedActions 使用字符串数组，例如 `["CLAIM", "REPORT"]`。前端据此显示操作，后端仍再次鉴权。

公开 DTO 不返回 openid、联系方式和证明。引用已停用字典时，保留历史名称。

## 5. 关闭与标记解决（B）

| 方法 | 路径 | 请求 |
|---|---|---|
| POST | `/posts/{id}/close` | expectedVersion、reason |
| POST | `/posts/{id}/resolve` | expectedVersion |

仅本人操作，通过工作流同步关联申请。

- OPEN 可以合法关闭或手动解决。
- PROCESSING 返回 STATE_CONFLICT，应先撤销或完成交接。
- LOST 若关联已接受申请，应先处理该交接，不能单独标记解决。

## 6. AI 提取（C）

### 6.1 接口与权限

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/ai/extraction-jobs` | 创建任务，返回 202 |
| GET | `/ai/extraction-jobs/{id}` | 任务本人查询 |

创建字段：

| 字段 | 要求 |
|---|---|
| text | 与 fileIds 至少提供一种 |
| fileIds | 本人上传的 POST_IMAGE |
| clientTime | 解释“昨天”等相对时间 |
| clientRequestId | 请求去重 |

不能拿私密证明文件请求公共识别。

### 6.2 查询结果示例

下面只展示统一响应中的 data：

```json
{
  "jobId": "3001",
  "state": "SUCCEEDED",
  "runSeq": 1,
  "inputHash": "opaque-input-digest",
  "result": {
    "categoryId": "12",
    "color": "黑色",
    "brand": null,
    "appearance": ["银色杯盖"],
    "suggestedDescription": "黑色保温杯，银色杯盖。",
    "locationId": null,
    "timePrecision": "UNKNOWN",
    "eventDate": null,
    "eventAt": null,
    "timePeriod": null,
    "needsConfirmation": ["categoryId", "color", "appearance"]
  },
  "error": null
}
```

| state | 含义 |
|---|---|
| QUEUED | 排队 |
| RUNNING | 执行中 |
| SUCCEEDED | 完成 |
| FAILED | 最终失败 |
| SUPERSEDED | 输入版本已过时 |

尚无结果时 result=null，不把任务状态转换成虚构进度百分比。

## 7. 匹配推荐（C）

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/posts/{id}/match-jobs` | 本人请求刷新，按版本与算法去重 |
| GET | `/posts/{id}/match-jobs/{jobId}` | 本人查询该信息的匹配任务 |
| GET | `/posts/{id}/matches` | 查看有效推荐 |

正常发布和编辑后端自动入队；恢复展示、撤销交接同样触发。手动刷新需要本人、OPEN、VISIBLE，并限流。

任务查询同时校验 jobId 的类型、targetId、ownerId，不能拿提取任务号或其他信息任务号读取。读取推荐要求源信息可见或具备本人历史权限，推荐项只包含可公开信息。

公开 matches 不返回 jobId、错误栈或任务输入。首个结果尚未产生时 items=[]、refreshState=QUEUED/RUNNING；不是伪造成功。终态同版本任务可冷却后重排，递增 run_seq。

| 响应字段 | 含义 |
|---|---|
| refreshState | 任务执行状态 |
| sourceVersion | 源信息内容版本 |
| mode | RULE_BASED 或 HYBRID |
| semanticStatus | PENDING、AVAILABLE、PARTIAL、UNAVAILABLE |
| items | PostCard，加 rank、reasons、mode |

规则可用、语义失败时返回 RULE_BASED 和 UNAVAILABLE。任务完成且 items=[] 表示没有合适推荐。

不返回任务原始输入，也不把排序分展示为归属概率。

## 8. 线索（B）

| 方法 | 路径 | 权限 |
|---|---|---|
| POST | `/posts/{id}/clues` | 登录用户，针对有效 LOST |
| GET | `/posts/{id}/clues` | 寻物发布者 |
| GET | `/me/clues` | 本人提交的线索 |

提交字段：content、sightingAt、locationId、imageIds、clientRequestId。时间地点可不确定；附件限本人正确用途的文件。

## 9. 认领与交接（B）

### 9.1 接口列表

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/posts/{id}/claims` | 申请认领，返回 201 |
| GET | `/me/claims` | direction=sent 或 received，status 可选 |
| GET | `/claims/{id}` | 相关双方查看详情 |
| POST | `/claims/{id}/accept` | 拾取者接受，附 finderContact |
| POST | `/claims/{id}/reject` | 拾取者拒绝，附 reason |
| POST | `/claims/{id}/cancel` | PENDING 申请人；ACCEPTED 任一交接方，附 reason |
| POST | `/claims/{id}/complete` | 拾取者确认实际归还 |

申请仅针对他人的有效 FOUND。拒绝限 PENDING；PENDING 仅申请人撤销，ACCEPTED 任一交接方可取消；完成限 ACCEPTED 的招领发布者。

所有认领动作、关闭、解决、管理下架请求带 clientRequestId。事务内先检查幂等结果，再校验状态；相同请求重试返回原结果。不同新请求遇到终态返回 STATE_CONFLICT。

### 9.2 认领请求示例

```json
{
  "clientRequestId": "f933be46-52dc-4b57-bb77-1eb067969034",
  "expectedFoundContentVersion": 1,
  "relatedLostPostId": "1008",
  "proofText": "杯底有姓名缩写，杯盖内侧有特殊标记。",
  "proofImageIds": ["901"],
  "applicantContact": {
    "type": "WECHAT",
    "value": "自愿填写的交接账号"
  }
}
```

relatedLostPostId 可空；非空须属于申请人、类型为 LOST，并处于可关联状态。接受时锁定并复核：已解决或正在其他交接中时返回冲突。多份 PENDING 可以引用同一 LOST，但最多一份进入 ACCEPTED。

创建时 expectedFoundContentVersion 来自当前招领详情，防止用户针对旧描述申请。后端保存两端当时内容版本，接受时再次比较；不一致返回 CLAIM_CONTENT_CHANGED。申请列表和详情返回 stale=true，提示撤销后重新申请，不自动改写旧核验材料。

### 9.3 私密字段的返回规则

| 内容 | 谁能读 |
|---|---|
| 证明 | 本申请人、招领发布者；管理端第一版默认不可读原始证明 |
| 申请人联系方式 | 本人可读自身字段；对方仅 ACCEPTED/COMPLETED |
| 拾取者联系方式 | 接受时提供；对方仅 ACCEPTED/COMPLETED |
| 证明图片 | 鉴权后短期许可 |

这些内容不进入普通列表或通知；证明文字不以原始 HTML 渲染。

## 10. 消息（B）

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/notifications` | 本人消息分页，unreadOnly 可选 |
| GET | `/notifications/unread-count` | 返回 count |
| PATCH | `/notifications/{id}/read` | 收件人幂等标记已读 |

## 11. 举报与管理（D）

除管理员登录外，admin 路径全部校验 ADMIN。

| 方法 | 路径 | 用途 |
|---|---|---|
| POST | `/reports` | 用户举报 postId、reasonCode、description |
| POST | `/admin/auth/login` | username、password 登录 |
| GET | `/admin/posts` | 查询信息及管理状态 |
| GET | `/admin/posts/{id}` | 管理信息详情，仅摘要和物品图，不含私密证明 |
| PATCH | `/admin/posts/{id}/moderation` | 下架或恢复，填写 reason |
| GET | `/admin/users` | 用户列表 |
| PATCH | `/admin/users/{id}/status` | 限制或恢复，限制时撤销会话 |
| GET | `/admin/reports` | 举报列表 |
| PATCH | `/admin/reports/{id}` | 处理结论和原因 |
| GET | `/admin/statistics` | 统计 |
| GET、POST | `/admin/categories` | 分类查询、新增 |
| PATCH | `/admin/categories/{id}` | 分类编辑、排序、停用 |
| GET、POST | `/admin/locations` | 地点查询、新增 |
| PATCH | `/admin/locations/{id}` | 地点编辑、停用 |

下架必须经过工作流，不只修改管理字段。请求同时带 expectedVersion、clientRequestId。管理员信息列表必须返回 rowVersion。

下架 LOST 同样处理其关联交接；恢复展示对合法 OPEN 信息重新入队。字典 enabled=false 是停用，不删除历史引用。

统计口径：待认领=可见 FOUND 且 OPEN；已归还=FOUND 且 RESOLVED。寻物解决数单独统计，避免重复计数。

## 12. 业务错误码速查

| 类别 | 错误码 |
|---|---|
| 参数与身份 | INVALID_ARGUMENT、UNAUTHENTICATED、FORBIDDEN、NOT_FOUND |
| 账号 | ACCOUNT_RESTRICTED |
| 状态与版本 | STATE_CONFLICT、POST_VERSION_CONFLICT |
| 认领 | ACTIVE_CLAIM_EXISTS、CLAIM_ALREADY_ACCEPTED、LOST_ALREADY_RESERVED、CLAIM_CONTENT_CHANGED |
| 重复请求 | IDEMPOTENCY_CONFLICT |
| 文件 | FILE_TOO_LARGE、FILE_PURPOSE_MISMATCH、FILE_TYPE_UNSUPPORTED |
| 频率与额度 | RATE_LIMITED、AI_QUOTA_EXCEEDED |
| AI 执行 | AI_PROVIDER_TIMEOUT、AI_INVALID_OUTPUT、AI_PROVIDER_UNAVAILABLE、AI_DISABLED |

AI 创建任务成功后，后续模型失败体现在查询到的任务 error 中，不把已接受的请求改成“未创建”。

下一步：[小程序设计](05-miniprogram.md) · [AI 与匹配](06-ai-and-matching.md) · [测试验收](07-testing.md)

images 每项含 fileId、url、sortOrder，保证编辑回填。timePeriod 固定 MORNING、AFTERNOON、EVENING。

公开分类与地点接口也采用统一分页；A 根据 total 获取完整选项，不假设默认第一页就是全部字典。私密申请返回申请人和拾取者的最小展示资料，不返回完整用户实体。
