# 微信小程序

**整个目录由 A 主维护。** B/C/D 提供后端接口和示例，不直接拆写页面或组件。

当前为目录骨架，未创建 app.json、app.ts 和项目配置，尚不能导入为可运行工程。

## 目录

| 目录 | 内容 |
|---|---|
| pages/ | 首页、发布、消息、我的 |
| packages/ | 信息、匹配、认领、账号业务分包 |
| components/ | 全部公共组件，包括 AI 草稿与图片上传 |
| services/business/ | 调用 B 的信息、认领、通知 |
| services/intelligence/ | 调用 C 的 AI、匹配 |
| services/platform/ | 调用 D 的身份、文件、字典、举报 |
| utils/ | 请求、上传、登录、轮询 |
| config/ | 环境地址，无服务端密钥 |

services 的三个分组全部由 A 维护，只区分 API 来源。

初始化选择原生 TypeScript 工程，保留现有目录设计。页面与组件统一四文件命名，复用表单与卡片降低工作量。

参见 [小程序设计](../docs/05-miniprogram.md)、[接口说明](../docs/04-api-contracts.md)、[文件归属](../docs/11-file-ownership.md)。
