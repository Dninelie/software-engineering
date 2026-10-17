# 文件与目录归属

本文件直接回答“我应该在哪些文件里开发”。所有路径相对 `campus-lost-found/`。

> 下列目录已建立；业务代码文件仍待创建。类名和文件名是开发约定，不代表已经实现。

## 1. 一张表定位

| 成员 | 主维护目录 |
|---|---|
| A | miniprogram/、tests/miniprogram/ |
| B | backend/.../modules/business/ |
| C | backend/.../modules/intelligence/、tests/ai-evaluation/ |
| D | backend/.../modules/platform/、backend/.../common/、admin-web/、deploy/ |

后端完整前缀：`backend/src/main/java/com/campus/lostfound/`。

## 2. A：小程序所有文件

```text
miniprogram/
├── pages/                          四个主包入口
│   ├── home/
│   ├── publish/
│   ├── messages/
│   └── me/
├── packages/
│   ├── post/                       detail、edit、mine
│   ├── matching/                   results
│   ├── recovery/                   clue-create、clues、apply、list、detail
│   └── account/                    profile、report
├── components/                     全部公共组件，包括 AI 面板
├── services/
│   ├── business/                   调 B 的业务接口
│   ├── intelligence/               调 C 的 AI、匹配接口
│   └── platform/                   调 D 的登录、文件、字典接口
├── utils/                          请求、登录、上传、轮询
└── config/                         环境地址
```

页面与组件内统一采用 index.ts、index.wxml、index.wxss、index.json。

### 拟建工具与 API 文件（全部 A 维护）

| 文件 | 内容 |
|---|---|
| services/business/post.ts | 发布、查询、编辑 |
| services/business/recovery.ts | 线索、认领、归还 |
| services/business/notification.ts | 消息 |
| services/intelligence/ai.ts | 提取任务 |
| services/intelligence/matching.ts | 推荐与刷新 |
| services/platform/account.ts | 登录和资料 |
| services/platform/asset.ts | 上传、图片许可 |
| services/platform/dictionary.ts | 类别、地点 |
| services/platform/report.ts | 举报 |
| utils/request.ts、auth.ts、upload.ts、job-poller.ts | 请求、身份、上传、任务轮询 |
| app.ts、app.json、app.wxss、project.config.json | 初始化、路由、样式、项目配置 |

B/C/D 只提供接口和响应示例，不直接维护这些文件。小程序私人配置不提交。

## 3. B：业务后端

```text
modules/business/
├── post/
├── recovery/
└── notification/
```

每个模块内部均有 api、application、domain、infrastructure。

### 拟建主要文件

| 路径 | 内容 |
|---|---|
| post/api/PostController.java | 发布、列表、编辑 |
| post/application/PostCommandService.java | 写正式信息、特征、关联图片 |
| post/application/PostQueryService.java | 只读列表、详情、候选 |
| post/application/PostMatchGuard.java | 供 C 提交时按序锁定公开投影 |
| post/application/AdminBusinessQuery.java | 供 D 管理端查询摘要 |
| post/application/PostStateService.java | 信息状态转换 |
| post/domain/Post.java、PostStatus.java | 信息对象、状态 |
| post/infrastructure/PostMapper.java | 信息持久化 |
| recovery/api/ClueController.java | 线索 |
| recovery/api/ClaimController.java | 认领与交接 |
| recovery/api/PostLifecycleController.java | 关闭、手动解决 |
| recovery/application/RecoveryWorkflowService.java | 接受、取消、归还、下架关联流程 |
| recovery/domain/Claim.java、ClaimStatus.java | 申请对象、状态 |
| recovery/infrastructure/ClaimMapper.java、ClueMapper.java | 认领、线索持久化 |
| notification/api/NotificationController.java | 消息 API |
| notification/application/NotificationService.java | 通知创建、去重、已读 |
| notification/infrastructure/NotificationMapper.java | 消息持久化 |

表：post、post_feature、post_asset、clue、clue_asset、claim、claim_asset、notification。

Mapper XML 放 `backend/src/main/resources/mapper/business/`。

## 4. C：AI、匹配和任务

```text
modules/intelligence/
├── ai/
├── matching/
└── job/
```

### 拟建主要文件

| 路径 | 内容 |
|---|---|
| ai/api/AiExtractionController.java | 提取任务 API |
| ai/application/AiExtractionService.java | 提取用例 |
| ai/application/ExtractFeaturesJobHandler.java | 提取任务处理 |
| ai/domain/FeatureExtractionGateway.java | 图文能力接口 |
| ai/domain/TextEmbeddingGateway.java | 向量能力接口 |
| ai/infrastructure/FeatureExtractionClient.java | 图文服务适配 |
| ai/infrastructure/TextEmbeddingClient.java | 向量服务适配 |
| matching/api/MatchingController.java | 推荐、刷新 |
| matching/application/MatchingService.java | 匹配用例 |
| matching/application/RefreshMatchesJobHandler.java | 匹配任务处理 |
| matching/domain/MatchingPolicy.java | 规则与语义排序 |
| matching/infrastructure/MatchResultMapper.java | 匹配关系持久化 |
| job/application/JobService.java | 同事务入队、任务状态 |
| job/application/JobScheduler.java | 调度与执行 |
| job/domain/JobHandler.java、JobState.java | 处理器合同、任务状态 |
| job/infrastructure/JobMapper.java | 领取、租约、恢复 |

表：ai_draft、post_embedding、match_result、ai_call_log、job。

Mapper XML 放 `backend/src/main/resources/mapper/intelligence/`。评测数据与记录放 `tests/ai-evaluation/`。

## 5. D：平台后端、管理端与部署

```text
modules/platform/
├── identity/
├── asset/
└── moderation/
```

### 拟建主要文件

| 模块 | 文件与内容 |
|---|---|
| identity/api | AuthController.java、ProfileController.java |
| identity/application | IdentityService.java |
| identity/infrastructure | SecurityConfig.java、用户与会话 Mapper |
| asset/api | AssetController.java |
| asset/application | AssetService.java |
| asset/domain | StorageGateway.java、FileAccessPolicy.java |
| asset/infrastructure | LocalStorageAdapter.java、AssetMapper.java |
| moderation/api | ReportController、AdminPostController、AdminUserController、DictionaryController、StatisticsController |
| moderation/application | ModerationService、DictionaryService、StatisticsService |
| moderation/infrastructure | 字典、举报、管理日志 Mapper |

涉及线索、证明的 FileAccessPolicy 可由 B 提供只读业务策略实现，D 维护接口和验证入口。策略只依赖查询，避免与写用例相互注入。

表：用户、管理员凭据、会话、分类地点、file_asset、举报、管理日志和幂等记录。

### 其他范围

| 路径 | 责任 |
|---|---|
| admin-web/ | 所有 Vue 页面、组件、路由与 API |
| backend/.../common/ | 公共返回、错误、幂等基础 |
| scripts/verify-design.mjs | 静态设计检查，D 主维护，B/C 补充断言 |
| backend/pom.xml | 后端依赖和构建，待建 |
| backend/.../LostFoundApplication.java | 启动类，待建 |
| backend/src/main/resources/application.yml | 公共配置，待建 |
| backend/src/main/resources/mapper/platform/ | 平台 Mapper XML |
| deploy/ | 环境模板、部署与恢复 |

D 管理管理员端路由，不直接改 B 的申请表；下架调用 B 的工作流。

## 6. 测试与迁移归属

| 目录 | 主责 |
|---|---|
| tests/miniprogram/ | A：学生端交互与真机 |
| backend/src/test/java/com/campus/lostfound/modules/business/ | B：状态、事务、权限 |
| backend/src/test/java/com/campus/lostfound/modules/intelligence/ | C：模型、排序、任务 |
| backend/src/test/java/com/campus/lostfound/modules/platform/ | D：身份、文件、管理 |
| backend/src/test/java/com/campus/lostfound/common/ | D：公共基础 |
| tests/api/business/、fixtures/business/ | B：业务接口样例和数据 |
| tests/api/intelligence/、fixtures/intelligence/ | C：AI 接口样例和数据 |
| tests/api/platform/、fixtures/platform/ | D：平台接口样例和字典 |
| tests/acceptance/ | A 组织整体验收，各人提供证据 |

Flyway 仍使用共享的 `backend/src/main/resources/db/migration/`。D 协调编号，每个人写自己表的脚本，不提前划分会破坏执行顺序的版本区间。

## 7. 文档怎么维护

| 文档 | 主维护人 |
|---|---|
| 小程序设计 | A |
| 需求业务规则、业务接口、业务表 | B |
| AI 与匹配、任务、AI 表、评测 | C |
| 部署、平台接口、平台表、公共约定 | D |
| 总体需求、架构、计划 | 四人确认 |

本文件描述目录边界；更详细的业务交接见 [分工说明](02-modules-and-team.md)。没有生成 GitHub CODEOWNERS，因为尚未提供成员账号。
