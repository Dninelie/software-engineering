# 校园失物招领与 AI 线索匹配平台

面向校园的失物发布、线索匹配与认领归还平台。AI 帮助整理特征和推荐相关信息，最终由双方核验归属。

> 当前进度：已建立目录和设计文档，尚未初始化可运行工程。

## 1. 四个人各自维护哪里

| 成员 | 主要范围 | 独立交付 |
|---|---|---|
| A | miniprogram/ | 完整学生端，包含 AI 和认领页面 |
| B | backend 的 business 区域 | 信息、线索、认领、归还、通知 |
| C | backend 的 intelligence 区域 | AI、匹配、持久任务与评测 |
| D | backend 的 platform、common；admin-web/、deploy/ | 登录、文件、管理后台、工程和部署 |

**按区域维护文件，通过接口协作。** B、C、D 提供 API 和示例，A 统一开发所有小程序交互。

## 2. 目录

```text
campus-lost-found/
├── miniprogram/                       A：整个微信小程序
├── backend/
│   └── src/main/java/com/campus/lostfound/
│       ├── modules/
│       │   ├── business/              B：post、recovery、notification
│       │   ├── intelligence/          C：ai、matching、job
│       │   └── platform/              D：identity、asset、moderation
│       └── common/                    D：统一返回、错误与公共基础
├── admin-web/                         D：管理后台
├── deploy/                            D：部署与环境模板
├── tests/                             按职责保存联调、验收与评测
├── docs/                              需求与设计文档
└── ARCHITECTURE.md                     总体架构
```

三个后端区域仍属于一个 Spring Boot 应用，不是三个服务。每个模块内部保留 api、application、domain、infrastructure 四层。

课程资料位于项目外同级的 `../CourseDocument/`，不属于项目。

## 3. 从哪里读起

| 目的 | 文档 |
|---|---|
| 初次了解 | [项目概览](docs/00-project-overview.md) |
| 看技术方案 | [总体架构](ARCHITECTURE.md) |
| 领取任务 | [四人分工](docs/02-modules-and-team.md) |
| 对应到文件 | [文件与目录归属](docs/11-file-ownership.md) |
| 查接口、数据和流程 | [文档导航](docs/README.md) |
| 排开发顺序 | [实施计划](docs/09-implementation-plan.md) |

## 4. 第一版流程

```text
发布 → 查看推荐 → 提供线索或申请认领 → 私密核验 → 交接归还
```

没有照片也能发布；AI 不可用时保留手动填写、搜索、规则推荐和认领。

接口变更同步文档。密钥与真实隐私不提交。精确依赖、模型服务与环境地址在首轮可行性验证后锁定。
