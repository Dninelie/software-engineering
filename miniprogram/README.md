# 微信小程序

整个目录归 A，采用原生 TypeScript、WXML、WXSS。

三个底部入口：首页、发布、我的。详情与认领分包；编辑复用发布页，匹配放详情，AI 放表单。

当前只有目录，没有 app.json 等工程文件，不能直接运行。

services 按 business、intelligence、platform 区分接口来源，全部由 A 维护。后台三人提供 API 和示例，不拆写页面。

参见 [文件分工](../docs/02-modules-and-team.md)、[接口](../docs/04-api-contracts.md)、[小程序与 AI](../docs/05-miniprogram-and-ai.md)。
