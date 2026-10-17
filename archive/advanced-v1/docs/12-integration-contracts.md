# 跨区域对接约定

文件边界解决“谁改代码”，本文件解决“怎样协作”。A/B/C/D 分工见 [分工说明](02-modules-and-team.md)。

以下固定内部服务的最小输入、输出和事务语义，Java DTO 随工程初始化创建；这些不是新增 HTTP 或微服务接口。

## 1. 客户端只有一个维护人

A 维护全部小程序代码。B、C、D 分别维护自己的后端接口，交付给 A：

- 成功、空、失败和权限不足示例。
- 字段类型与是否可空。
- 状态和动作限制。
- 稳定错误码、分页规则。
- 服务可用环境与模拟切换方式。

C 不直接写 AI 面板；D 不直接写上传组件；B 不直接写认领页面。

D 独立维护 Vue 管理后台，其操作复用后端能力。

## 2. D → 其他人：身份与文件

| 能力 | 约定 |
|---|---|
| 当前用户 | 由后端令牌确定，不信任前端 ownerId |
| 账号状态 | 所有写操作检查是否受限 |
| 附件验证 | 上传者、用途、数量、关联状态 |
| 私密读取 | 验证业务权限后签发短期许可 |
| 幂等基础 | 同一键同一请求只产生一次业务效果 |

B 定义证明和线索的参与者权限；D 维护统一文件入口。只读权限策略不能依赖正在调用文件服务的写用例，避免循环注入。

## 3. B → C：发布入队

B 在发布/编辑事务内完成：

```text
信息 + 正式特征 + 图片关联 + 内容版本 + C 的 JobService 入队
```

JobService 使用同一数据源与当前事务，不另开独立提交事务。入队只写 job，不同步运行 handler。

事务失败时信息和任务一起回滚；提交后后台才能看到任务。

目标至少包含 postId、contentVersion、用户和去重标识。不把敏感证明或整张用户记录放入任务输入。

## 4. C → B：只读候选与通知

| 服务 | C 可以做什么 | 限制 |
|---|---|---|
| PostQueryService | 读取可见的公开物品投影与版本 | 只读，不返回证明和联系方式 |
| NotificationService | 为新匹配关系创建去重通知 | 不直接使用 notification Mapper |

C 保存 intelligence 自己的结果，通过上述服务协作。

B 的查询服务不依赖 JobService。C 的 JobService 不依赖 MatchingService。调度器在后台再选 handler，避免发布服务与匹配服务互相注入。

## 5. D → B：管理下架

D 检查管理员身份、原因后调用 B 的工作流。

一个数据库事务内协调：

1. 信息管理状态改为 HIDDEN。
2. 未完成申请结束，必要的 PROCESSING 状态恢复。
3. 创建站内通知。
4. 保存管理日志。

不能只改 HIDDEN 让申请一直停在 ACCEPTED。恢复展示也不恢复已经结束的申请。

## 6. A → B/C/D：前端联调

小程序 services 分组：

| 目录 | API 提供者 | 客户端维护者 |
|---|---|---|
| business/ | B | A |
| intelligence/ | C | A |
| platform/ | D | A |

A 的请求封装统一处理 token 和错误，但不自动重试全部写请求。相同用户操作的网络重试保持幂等键。

页面显示以 allowedActions 和当前任务结果为准，后端仍再次检查状态和权限。

## 7. 固定内部服务的最小合同

| 服务与提供者 | 输入 | 输出与事务 |
|---|---|---|
| C：JobService.enqueueMatch | postId、contentVersion、rowVersion、algorithmVersion、ownerId | jobId、state、runSeq；加入当前事务，只入队 |
| B：PostQueryService.getMatchProjection | postId | 公开投影、状态、两种版本；无证明 |
| B：PostQueryService.findCandidates | 源投影、游标、上限 | 稳定排序的有限候选，不装饰私密 URL |
| B：NotificationService.createOnce | 收件人、类型、业务 ID、去重键、安全摘要 | 已有或新通知 ID，加入当前事务 |
| B：RecoveryWorkflowService.moderate | 信息 ID、版本、目标状态、管理员、原因 | 业务状态结果；不直接写 D 的日志表 |
| D：AssetService.validateAndAttach | 用户、文件 ID、用途、业务引用 | 验证并关联，加入当前事务 |
| D：FileAccessPolicy；B 的 BusinessFileAccessPolicy 实现 | 用户、文件、业务引用 | 允许/拒绝；只读策略 |
| D：ModerationService | 管理请求与幂等键 | 外层事务调用 B 工作流，再写 D 日志 |
| B：PostMatchGuard.lockPair | 两个信息 ID、预期版本 | 当前事务内按序锁定并返回公开投影；不调用 C |
| B：AdminBusinessQuery | 已验证管理员上下文、筛选或信息 ID | 管理摘要和物品图引用，无证明、联系方式 |
| D：DictionaryQuery | 分类/地点 ID 或启用列表 | 只读字典，供 C 校验 AI 输出 |

NotificationService 不反向调用匹配服务。PostQueryService 不依赖 AssetService，图片 URL 在独立响应装配器生成。

AssetService 可以调用 B 的只读文件权限策略；该策略只依赖业务查询 Mapper，不依赖 AssetService、管理服务或写用例。

PostCommandService → JobService → JobMapper；MatchingHandler → PostQueryService → PostMapper。不要通过 @Lazy 或允许循环引用掩盖依赖错误。

C 提交结果通过 B 的 PostMatchGuard 获取锁，不跨区域使用 PostMapper。D 管理查询通过 B 的 AdminBusinessQuery，不跨区域读业务 Mapper。

后台线程没有微信请求或 SecurityContext。API 从身份中生成可信 ActorContext；任务以 jobId、ownerId、用途生成限定 TaskActor。文件服务显式接收该上下文并验证用户状态、文件用途和任务引用，不能在 handler 中依赖请求线程的 CurrentUser。

关键公开事务方法通过 Spring 代理调用；不能依赖同类内部调用自动开启事务。使用同一数据源、同一事务管理器，回滚规则覆盖业务异常。

## 8. 并发与统一锁顺序

先读取不可变关联 ID，收集全部受影响对象，再按顺序锁定：

```text
幂等记录 → 所有受影响 post（ID 升序）→ claim（ID 升序）
        → file_asset → job → 派生结果 → 通知和日志
```

关联集合变化时回滚重试，不能持有后面的锁再补前面的锁。初步查询不作为最终校验，锁定后用当前读复核。

- 创建申请也锁 FOUND 和非空关联 LOST，检查重复活动申请。
- 接受时同时检查 FOUND 和 LOST 没有其他 ACCEPTED。
- 创建申请保存双方内容版本，接受时比较；LOST 有 ACCEPTED 时阻止普通编辑和关闭。
- ACCEPTED 双方可取消，恢复 FOUND 并入队；终态不能取消。
- 完成、关闭、解决、下架两种类型都使用同一锁顺序。
- 匹配提交先锁双方 post，再锁 job，验证租约、runSeq、版本和可见状态。
- 调度领取仅短暂锁 job，提交释放后再执行 handler，不持 job 锁回调业务。
- 同版本、同算法的 HYBRID 不被迟到 RULE_BASED 覆盖；内容或算法变化则旧结果失效。

## 9. 去重、恢复与负载

去重键包含 postId、rowVersion、algorithmVersion。contentVersion 另存，不能只凭它区分恢复后的任务。

同键 QUEUED/RUNNING 时复用；终态冷却后可重排，递增 runSeq，换租约。提交与续租同时校验租约和 runSeq。

提取请求可以因配额或队列上限拒绝。业务刷新入队不因模型额度、线程繁忙或模型不可用而拒绝，可合并任务并规则降级。数据库本身不可用时发布仍需失败，不能假装保存。

暂不自动清理上传文件。启用清理前，D 必须通过 B/C 的只读引用查询排除业务、草稿及未终止任务引用；验证未通过前保留文件。

## 10. 合同变更流程

1. 接口提供者修改文档，标出字段和错误行为变化。
2. 调用方确认页面或服务影响。
3. 提供固定示例供调用方先联调。
4. 双方更新实现并验证。
5. 更新对应测试和验收证据。

迁移由各区域自己编写，D 协调执行编号。公共构建和启动配置由 D 合并，不各自建一套工程。

返回：[接口说明](04-api-contracts.md) · [文件归属](11-file-ownership.md)
