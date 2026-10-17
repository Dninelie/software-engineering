# 数据库：六张表

本文件固定字段与索引，供 B/D 编写 schema.sql。当前尚无实际建表脚本，不表示已执行。

## 1. 通用约定

- MySQL、InnoDB、utf8mb4，ID 为 BIGINT 自增，接口用字符串。
- 各表有 created_at、updated_at，类型 DATETIME(3)。
- 时间点按 UTC 存储，接口输出带时区的 ISO 8601；event_date 是校园日期，不转换为 UTC。
- 枚举用 VARCHAR，应用层检查；不物理删除已引用用户或信息。
- C 不建表；类别地点使用 D 的固定字典。

## 2. app_user（D）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id | BIGINT | 主键 |
| openid | VARCHAR(128) NULL | UNIQUE，微信用户填写 |
| nickname | VARCHAR(64) | 业务限制 1–30 字 |
| role | VARCHAR(16) | USER/ADMIN |
| username | VARCHAR(64) NULL | UNIQUE，仅管理员 |
| password_hash | VARCHAR(255) NULL | 管理员密码哈希 |
| token_hash | CHAR(64) NULL | UNIQUE，SHA-256 十六进制 |
| token_expires_at | DATETIME(3) NULL | 到期时间 |

后端生成安全随机 token，仅登录时返回原值。每人同时一个登录态，新登录替换旧 token；退出只清除当前 token，不能误清后续新登录。

首次微信登录按 openid 创建默认用户。并发首次登录依靠唯一键返回同一账号，不创建重复用户。管理员由 D 初始化，密码用成熟哈希工具。

## 3. post（B）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id、owner_id | BIGINT | 主键、发布者引用 |
| type | VARCHAR(8) | LOST/FOUND，不可修改 |
| title | VARCHAR(50) | 5–50 字 |
| category_code | VARCHAR(32) | 固定类别 |
| location_code | VARCHAR(32) | 固定地点，允许 UNKNOWN |
| event_date | DATE NULL | 大致日期 |
| description | VARCHAR(1000) | 公开描述 |
| color、brand | VARCHAR(30)、VARCHAR(80) | 默认空字符串 |
| features | VARCHAR(300) | 默认空字符串 |
| status | VARCHAR(16) | 四种信息状态 |
| visible | BOOLEAN | 默认 true |
| version | INT | 默认 1，编辑或状态/可见性变化递增 |

建议索引：(type,visible,status,category_code,created_at)、(owner_id,created_at)。

更新时在事务中锁信息，比较 expectedVersion，再更新。拒绝申请但未改变帖子状态时，不必增加帖子 version。

## 4. file_asset（D）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id、owner_id | BIGINT | 主键、上传者 |
| post_id | BIGINT NULL | 未发布时为空 |
| storage_key | VARCHAR(255) | UNIQUE，随机生成 |
| mime_type | VARCHAR(32) | image/jpeg 或 image/png |
| byte_size | BIGINT | 最大 5×1024×1024 |
| sort_order | INT | 默认 0，按 imageIds 顺序赋值 |

一个文件最多绑定一条本人信息；同帖保留关联允许，不能抢占其他帖附件。

编辑时把不再使用的图片解绑 post_id=NULL，新图片校验后绑定。文件本身暂不删除。按文件 ID 顺序锁定或用条件更新避免同图并发绑定。

已绑定、visible=true 的物品图可公开，包括结束信息的历史图；下架后返回 404。未绑定文件只供上传者的 AI 请求在后端读取，客户端使用本地预览。

不建私密图片或签名表，不启用自动清理。

## 5. claim（B）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id、found_post_id、applicant_id | BIGINT | 申请、招领、申请人 |
| proof_text | VARCHAR(1000) | 私密证明，对应接口 proof |
| applicant_contact | VARCHAR(100) | 申请时提交 |
| finder_contact | VARCHAR(100) | 默认空，接受时提交 |
| status | VARCHAR(16) | 五种申请状态 |
| reason | VARCHAR(500) | 默认空 |

索引：(found_post_id,status)、(applicant_id,created_at)。

不要给 (found_post_id,status) 加唯一约束，它会错误限制多份 PENDING。活动申请唯一与最多一人被接受，通过锁同一 post 后检查实现。

没有 relatedLostPostId、申请内容快照或算法版本。

## 6. clue（B）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id、lost_post_id、author_id | BIGINT | 主键、寻物、提交者 |
| content | VARCHAR(1000) | 文字线索 |

索引：(lost_post_id,created_at)。不附图、不存坐标；发布日期地点写在线索文字中。

## 7. report（D）

| 字段 | 类型建议 | 规则 |
|---|---|---|
| id、post_id、reporter_id | BIGINT | 主键、信息、举报人 |
| reason | VARCHAR(500) | 举报原因 |
| status | VARCHAR(16) | PENDING/HANDLED/IGNORED |
| result | VARCHAR(500) | 默认空 |

索引：(status,created_at)。第一版不自动下架，也不建审批或操作日志表。

## 8. 最少必须保留的事务

| 操作 | 顺序与结果 |
|---|---|
| 发布/编辑 | 锁需更新的信息，保存字段，与 D 的图片绑定同事务 |
| 创建申请 | 锁招领 → 查本人活动申请 → 检查状态和版本 → 插入 |
| 接受 | 锁招领 → 检查本人是拾取者、OPEN、申请 PENDING → 更新双方 |
| 拒绝/撤销待处理 | 锁招领 → 校验角色和申请状态 → 更新申请 |
| 取消交接 | 锁招领 → 申请 CANCELLED → 信息 OPEN、version+1 |
| 归还 | 锁招领 → 当前申请完成、其他 PENDING 拒绝 → RESOLVED |
| 关闭/下架 | 锁信息 → 更新帖子与受影响申请 |

申请的 found_post_id 创建后不可变。可先普通查询得到该 ID，再按固定顺序锁 post、查询申请；不要先锁申请再锁 post。

Python 使用 SQLAlchemy 2 同步 Session，锁查询用 with_for_update()。路由用 with session.begin() 管理事务，service/repository 接收同一个 session，不自行 commit。全应用共用一个 Engine 和 Session 工厂，模型请求不进入事务。

接受、完成或关闭前的最终状态检查必须在事务锁内，不使用前端读取时的旧状态。

## 9. 脚本交付

B 提供 post/claim/clue，D 提供 app_user/file_asset/report，D 合并 backend/sql/schema.sql 并确认索引、外键和建表顺序。ORM 映射分别放 app/business/models.py 和 app/platform/models.py，共用 common/database.py 的 Base；D 统一导入模型，防止表映射未注册。

第一版手动执行统一 SQL，不引入 Alembic；已有库变更由 D 提供显式 ALTER 脚本，不用 create_all 假装升级已有表。首次演示使用虚构用户、物品和证明，不提交真实 token 或密码。
