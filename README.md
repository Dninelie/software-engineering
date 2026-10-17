# 校园失物招领与 AI 辅助匹配平台

面向四人软件工程课设。目标是完成一条可演示的流程：

**发布 → 查找与推荐 → 申请认领 → 核验交接 → 确认归还。**

> 当前阶段：Python 版目录与设计已建立，尚无可运行工程。

技术方案：原生微信小程序（TypeScript）＋ Python 3.12 / FastAPI ＋ SQLAlchemy / MySQL，管理端 Vue。后端只有一个应用，AI 与普通业务使用同一套 Python 工程。

## 1. 第一版做什么

保留寻物、招领、搜索、文字线索、认领、基础管理，以及文字/图片 AI 辅助填写。

推荐先按类别、颜色、时间、地点和关键词计算。向量检索、消息中心、订阅推送和持久任务不作为第一版要求。

## 2. 四人分工

| 成员 | 主维护范围 |
|---|---|
| A | miniprogram/：全部小程序页面和接口调用 |
| B | backend/app/business/：信息、线索、认领、归还 |
| C | backend/app/intelligence/：AI 提取与规则推荐 |
| D | backend/app/platform/、common/、main.py；admin-web/、deploy/ |

## 3. 从哪里开始

1. [功能与规则](docs/01-requirements.md)
2. [分工与文件](docs/02-modules-and-team.md)
3. [总体架构](ARCHITECTURE.md)
4. [数据库](docs/03-database.md)
5. [接口说明](docs/04-api-contracts.md)
6. [小程序与 AI](docs/05-miniprogram-and-ai.md)
7. [开发与验收](docs/06-development-and-testing.md)

完整入口：[文档导航](docs/README.md)。

## 4. 当前目录

```text
campus-lost-found/
├── miniprogram/          A：学生端
├── backend/              B/C/D：一个后端
├── admin-web/            D：管理端
├── deploy/               环境与部署
├── docs/                 当前简化设计
├── tests/                验收和 AI 样例
├── scripts/              文档检查
└── archive/              旧复杂方案，仅备查
```

旧方案完整保存在 [归档说明](archive/README.md) 所列位置，不再作为当前实现要求。

第一版保持六张表、七个小程序页面、32 个业务接口。先共同建立最小可运行工程、固定公共类型，再按文件分工并行开发。后端启动目标与依赖计划见 [后端说明](backend/README.md)。

原课程资料仍位于项目外的同级 CourseDocument，未改动。
