# 接口说明与联调约定

统一前缀 /api/v1。只维护本文件，不增加大型 OpenAPI 或任务接口。

Python 后端采用 FastAPI，现有 32 个业务接口保持不变。开发时可用框架自动生成的 /docs、/openapi.json，不另外维护手写规范。

## 1. 公共格式

### 请求与成功返回

- JSON 字段使用 camelCase。
- ID 是字符串；日期为 YYYY-MM-DD；时间点是带时区 ISO 8601。
- 私有请求带 Authorization: Bearer <token>。
- 查询和动作成功 200，新建成功 201；前端接受全部 2xx。

```json
{
  "code": "OK",
  "message": "操作成功",
  "data": {}
}
```

分页统一 data={items,total,page,pageSize}。page 从 1 开始，pageSize 默认 20、最大 50；默认 createdAt、id 倒序。字典和推荐直接返回数组，不分页。

### 错误

| HTTP / code | 行为 |
|---|---|
| 400 / INVALID_ARGUMENT | 字段或文件类型错误 |
| 401 / UNAUTHENTICATED | 无登录态或过期，重新登录 |
| 403 / FORBIDDEN | 已登录但无权操作 |
| 404 / NOT_FOUND | 不存在或历史信息不可见 |
| 409 / STATE_CONFLICT | 状态不允许，刷新 |
| 409 / VERSION_CONFLICT | 详情过时，刷新后重做 |
| 413 / FILE_TOO_LARGE | 超过上传限制 |
| 503 / AI_UNAVAILABLE | AI 故障，手动填写 |
| 500 / INTERNAL_ERROR | 服务异常，不返回堆栈 |

错误结构仍为 code、message、data，其中 data=null。动作失败不自动重试 POST。

FastAPI 的 RequestValidationError 由 D 统一转为 400 / INVALID_ARGUMENT；身份依赖明确返回 401/403，避免默认错误格式与这里不同。文件内容成功返回二进制图片，其余成功响应使用 JSON 信封。

Python 字段用 snake_case，Pydantic schema 显式声明 camelCase 别名并按别名输出；查询参数同样使用这里的 camelCase。请求从字符串校验转换为内部 int ID，响应显式转为字符串，不依赖 Pydantic 自动把 int 转 str。日期/时区和空值保持本文件约定。请求 schema 禁止额外字段，防止 ownerId、role 等被悄悄接收。

## 2. D：身份、字典和图片

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /auth/wechat-login | code → 平台登录 |
| POST | /admin/auth/login | username、password → 管理员登录 |
| POST | /auth/logout | 撤销当前 token |
| GET | /me | 本人资料 |
| PATCH | /me | 更新 nickname |
| GET | /categories | code、name 数组 |
| GET | /locations | code、name 数组 |
| POST | /files | multipart，字段 file |
| GET | /files/{id}/content | 可公开的物品图片 |

公开入口：两个登录接口、字典、合法公开图片。其余身份操作须登录。图片与普通公开页面不因知道 ID 就绕过关联检查。

登录返回 data：

```json
{
  "token": "仅示例，不是真实凭证",
  "expiresAt": "2026-10-17T18:00:00+08:00",
  "user": {
    "id": "1001",
    "nickname": "校园用户",
    "role": "USER"
  }
}
```

GET/PATCH /me 返回上述 user 结构。角色由后端确定，不能通过 PATCH 修改。

微信登录请求为 {code}，由后端换取 openid；不接收客户端指定的 openid。管理员登录请求为 {username,password}。登录密码不写日志，失败统一 401。两个登录接口与 GET 字典不要求 token。

token 默认 8 小时，一个账号一个有效登录态。新登录替换旧 token。退出仅清除匹配的当前 token；过期或无效 token 返回 401，客户端仍可清本地状态。

### 上传

- 登录，JPEG/PNG，实际字节格式校验，单图最多 5MiB。
- 201 返回 {fileId}。先用本地路径预览，不公开未绑定文件。
- 正式发布提交有序 imageIds；后端检查本人、数量、关联。
- 绑定可见信息后，GET 返回真实 image/jpeg 或 image/png。
- Cache-Control: no-store；信息下架或文件解绑后返回 404。
- 没有签名图片接口，不支持认领证明图片。

## 3. B：信息接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /posts | 发布 |
| GET | /posts | 公开列表 |
| GET | /posts/{id} | 公开详情、本人或管理员历史 |
| PUT | /posts/{id} | 本人编辑 |
| GET | /me/posts | 我的发布 |
| POST | /posts/{id}/close | 本人 OPEN 信息关闭 |
| POST | /posts/{id}/resolve | 本人 OPEN 的 LOST 标记找回 |

GET /posts 参数：type、keyword、categoryCode、locationCode、page、pageSize。keyword 在标题、描述中匹配，最多 100 字。

公开列表/详情要求 visible=true 且 OPEN/PROCESSING；本人和管理员可读历史物品资料。GET /me/posts 可选 type、status 筛选。

### 发布与编辑请求

```json
{
  "type": "LOST",
  "title": "寻找黑色保温杯",
  "categoryCode": "CUP",
  "eventDate": "2026-10-16",
  "locationCode": "CANTEEN",
  "description": "黑色保温杯，昨天在食堂附近丢失。",
  "color": "黑色",
  "brand": "",
  "features": "银色杯盖，带提绳",
  "imageIds": []
}
```

POST 返回 201，data={id,version}。

PUT 使用相同可编辑字段，去掉 type，增加 expectedVersion。更新成功 200，data={id,version}。图片顺序由 imageIds 顺序决定，省略旧图片表示解绑。

ownerId、status、visible、type 不允许普通编辑。字段长度与空值统一见 [需求](01-requirements.md)。

### 列表和详情

| 结构 | 字段 |
|---|---|
| 列表项 | id、type、title、categoryCode、locationCode、eventDate |
| 列表展示 | status、thumbnailUrl、createdAt |
| 详情额外 | description、color、brand、features、version、visible |
| 发布者 | publisher={id,nickname} |
| 图片 | images=[{fileId,url}]，按顺序 |
| 交互提示 | isOwner、canEdit、canClaim |

没有图时 thumbnailUrl=null、images=[]。公开响应不含证明、联系方式、openid 或 token。

canEdit：本人、OPEN、visible，且 FOUND 没有活动申请。canClaim：登录、非本人、FOUND、OPEN、visible。未登录两者为 false。

close 请求 {reason}；resolve 不需要正文。成功返回 {id,status,version}。两者都在事务中检查状态，PROCESSING 返回 409。

close 同时拒绝 PENDING 并写原因；resolve 只用于 LOST。FOUND 实际归还通过 complete。

## 4. C：AI 辅助与推荐

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /ai/extract-features | 登录，文字/图片提取 |
| GET | /posts/{id}/matches | 本人 OPEN、visible 信息的规则推荐 |

### 提取请求

```json
{
  "text": "帮我描述这个保温杯",
  "fileIds": ["501"]
}
```

text 最多 2000 字，fileIds 最多 3 个；至少有一种有效输入。图片须本人上传，可未绑定或属于本人已有信息。

无权限图片拒绝，模型不直接接收磁盘路径。referenceDate 使用后端校园当天，日期不确定返回 null。

提取返回 data：

```json
{
  "categoryCode": "CUP",
  "eventDate": null,
  "color": "黑色",
  "brand": "",
  "features": "银色杯盖，带提绳",
  "description": "黑色保温杯，银色杯盖，带提绳。"
}
```

六个字段始终存在。categoryCode 未知时 null；其他未知文字用空字符串。日期必须合法且不晚于当天。没有足够信息时允许空建议，不编造内容。

模型超时或无有效结构返回 503，不保存草稿。成功建议仍需人工确认，不能自动发布。

### 推荐返回

data 为数组，最多 5 项，每项：

| 字段 | 说明 |
|---|---|
| id、type、title | 候选信息 |
| thumbnailUrl | 首图或 null |
| locationCode、eventDate | 地点与日期 |
| reasons | 实际命中条件的文字数组 |

候选必须公开、OPEN、相反类型、其他发布者。source 不属于本人 403，不是可匹配状态 409。没有合适候选返回 []。

推荐不调模型、不持久化。具体初始规则见 [AI 与页面](05-miniprogram-and-ai.md)。

## 5. B：文字线索

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /posts/{id}/clues | 登录，提交 {content} |
| GET | /posts/{id}/clues | 寻物发布者分页查询 |

提交要求：可见 OPEN 的 LOST、非本人，content 1–1000 字。201 返回 {id}。

列表项：id、content、author{id,nickname}、createdAt。不附图，无作者历史接口。寻物关闭后，发布者仍可查看已收到的线索。

## 6. B：认领与交接

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /posts/{id}/claims | 创建或返回本人的已有活动申请 |
| GET | /me/claims | direction=sent/received，分页 |
| GET | /claims/{id} | 相关双方详情 |
| POST | /claims/{id}/accept | 拾取者接受，{contact} |
| POST | /claims/{id}/reject | 拾取者拒绝，{reason} |
| POST | /claims/{id}/cancel | 按状态和角色取消，{reason} |
| POST | /claims/{id}/complete | 拾取者确认归还，无正文 |

### 创建请求

```json
{
  "postVersion": 1,
  "proof": "杯底有我的姓名缩写。",
  "contact": "交接用的微信或电话"
}
```

锁招领后先查本人的活动申请，已有就 200 返回 {id,status,existing:true}，不先被旧 postVersion 拦住。

没有活动申请时，再查 FOUND、非本人、OPEN、visible、版本和字段。201 返回 {id,status,existing:false}。

### 列表、详情与动作结果

direction 必填，可选 status、page、pageSize。received 只返回本人发布的 FOUND 上的申请。

| 结构 | 字段 |
|---|---|
| 列表项 | id、foundPostId、postTitle、status、createdAt、updatedAt |
| 列表展示 | applicant={id,nickname}、reason |
| 详情额外 | proof、finder={id,nickname}、applicantContact、finderContact、allowedActions |

proof 只在相关双方的详情中出现。两种 contact 本人可见自身字段；对方仅 ACCEPTED/COMPLETED 可见，其余阶段返回 null。尚未填写的 finderContact 也返回 null。管理员不额外获得读取权。

allowedActions 为 ACCEPT、REJECT、CANCEL、COMPLETE 的子集；终态 []。

动作成功返回 {id,status,foundPostId,postStatus,postVersion}，A 再刷新详情拿最新交接信息。

### 动作限制

- accept/reject：拾取者，PENDING；accept 还要求招领 OPEN、visible。
- cancel：PENDING 仅申请人；ACCEPTED 双方均可。
- complete：拾取者，ACCEPTED、招领 PROCESSING。
- 重复或非法动作统一 409，重新查询，不复活终态。
- 权限先于任何“已处理”结果检查，不能借重复请求越权。

## 7. D：举报与后台

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /reports | 登录，{postId,reason} |
| GET | /admin/posts | 管理信息分页 |
| POST | /admin/posts/{id}/hide | 下架，{reason} |
| GET | /admin/reports | 举报分页 |
| POST | /admin/reports/{id}/handle | {status,result} |

除管理员登录外，所有 /admin 路径校验 ADMIN。普通用户不能通过改 URL 管理。

举报只针对存在且当前公开的信息。201 返回 {id}，第一版不自动去重举报。

管理信息筛选：type、status、visible、keyword、page、pageSize。返回普通列表字段，加 visible、version。详情复用 GET /posts/{id} 管理权限，不含私密核验。

举报列表可按 status 筛选，返回 id、postId、postTitle、reason、status、result、createdAt。

handle 的 status 仅 HANDLED/IGNORED，result 1–500 字。只处理 PENDING，终态重复处理 409。

hide 调 B 的 business/services/posts.py 中 hide_post；同一 Session 事务设置 visible=false、未解决信息 CLOSED，拒绝 PENDING、取消 ACCEPTED。已 RESOLVED 保留该业务状态。重复下架返回当前结果，不重新处理申请。

hide 成功返回 {id,status,visible,version}；handle 成功返回 {id,status,result}。reason/result 的长度见需求字段表。

第一版不恢复下架信息，不把举报处理自动绑定下架。

## 8. 前端提交规则

禁用提交中的按钮，不自动重试全部 POST。网络结果不明时先刷新“我的发布”、申请或详情再决定是否重提。

401 保留输入并提示登录；409 刷新信息和可操作按钮；AI 503 提示手动继续。不能仅根据 HTTP 成功回调认定业务成功。
