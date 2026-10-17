# 管理后台

负责人 D，Vue＋TypeScript。当前为目录骨架，无 package.json 和可运行应用。

src/views：login/posts/users/reports/dictionaries/statistics。
src/services：调用 /api/v1/admin 接口；src/components/layouts/router/types：公共结构。

登录、权限由后端再次校验，前端路由守卫不构成安全边界。后台私密信息按管理用途最小展示，操作填写原因并记录日志。

参见 [模块分工](../docs/02-modules-and-team.md) 与 [接口合同](../docs/04-api-contracts.md)。
