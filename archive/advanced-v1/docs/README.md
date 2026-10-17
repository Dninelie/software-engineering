# 文档导航

先理解项目，再按自己的任务查阅详细设计，无需从头读完全部文档。

**文档状态：**开发前设计。接口、表结构和性能目标尚待实现与验证。

## 1. 第一次阅读

建议按下面的顺序阅读：

1. [项目概览](00-project-overview.md)：做什么、谁使用、怎样完成一次归还。
2. [需求规格](01-requirements.md)：第一版具体做哪些功能。
3. [总体架构](../ARCHITECTURE.md)：各端、后端和 AI 如何配合。
4. [四人分工](02-modules-and-team.md)：自己负责什么、与谁对接。
5. [实施计划](09-implementation-plan.md)：从哪一步开始。

遇到不熟悉的名词，可查阅 [术语说明](10-glossary.md)。

## 当前分工

A：整个小程序；B：业务后端；C：AI、匹配、任务；D：平台、管理后台、部署。

后端目录对应 business、intelligence、platform 三个区域。此前按业务拆小程序的分工已由 [新分工](02-modules-and-team.md) 取代。

## 2. 按开发任务查文档

| 当前任务 | 主要参考 | 对接参考 |
|---|---|---|
| 确定自己改哪些文件 | [文件与负责人对照](11-file-ownership.md) | [四人分工](02-modules-and-team.md) |
| 对接别人提供的能力 | [跨区域对接约定](12-integration-contracts.md) | [接口说明](04-api-contracts.md) |
| 写信息发布、搜索页面 | [小程序设计](05-miniprogram.md) | [接口说明](04-api-contracts.md) |
| 实现登录和文件上传 | [接口说明](04-api-contracts.md) | [部署与配置](08-deployment.md) |
| 建表、写迁移 | [数据库设计](03-database.md) | [需求与状态](01-requirements.md) |
| 接入 AI、实现匹配 | [AI 与匹配](06-ai-and-matching.md) | [数据库设计](03-database.md) |
| 实现认领与归还 | [需求与状态](01-requirements.md) | [接口说明](04-api-contracts.md) |
| 联调或准备答辩 | [测试与验收](07-testing.md) | [实施计划](09-implementation-plan.md) |

## 3. 每份文档负责什么

| 文档 | 回答的问题 | 维护人 |
|---|---|---|
| [00 项目概览](00-project-overview.md) | 项目是什么？如何使用？ | 四人 |
| [01 需求规格](01-requirements.md) | 功能、规则和状态是什么？ | 四人 |
| [总体架构](../ARCHITECTURE.md) | 系统怎样分层和协作？ | 四人 |
| [02 四人分工](02-modules-and-team.md) | 模块归谁？如何交接？ | 各负责人 |
| [03 数据库设计](03-database.md) | 存哪些数据？如何保证一致？ | D 组织 |
| [04 接口说明](04-api-contracts.md) | 前后端怎样交换数据？ | 各负责人 |
| [05 小程序设计](05-miniprogram.md) | 页面和组件怎样实现？ | A |
| [06 AI 与匹配](06-ai-and-matching.md) | 模型、任务和排序怎样实现？ | C |
| [07 测试与验收](07-testing.md) | 如何证明功能可靠？ | A 组织整体验收，各区域自测 |
| [08 部署与配置](08-deployment.md) | 系统怎样部署和配置？ | D |
| [09 实施计划](09-implementation-plan.md) | 开发顺序与待确认项是什么？ | 四人 |
| [10 术语说明](10-glossary.md) | 技术名词是什么意思？ | 四人 |
| [11 文件与负责人对照](11-file-ownership.md) | 每人负责哪些目录和拟建文件？ | 各负责人 |
| [12 跨区域对接约定](12-integration-contracts.md) | 怎样入队、查询、下架而不越过边界？ | B/C/D，A 反馈 |
| [13 设计审查](13-design-review.md) | 发现了什么问题，开工前还要验证什么？ | 四人 |
| [机器可读合同](contracts/README.md) | OpenAPI 和服务依赖图如何检查？ | B/C/D |

## 4. 使用规则

总体架构描述系统边界；需求文档确定业务规则；数据库和接口文档约定实现细节。发现冲突时，先统一约定再开发。

示例用于说明格式，不表示接口已可调用。验收模板也不表示测试已通过。

这些文件采用 Markdown，便于随代码一起维护；课程报告可在后续按教师模板汇编。
