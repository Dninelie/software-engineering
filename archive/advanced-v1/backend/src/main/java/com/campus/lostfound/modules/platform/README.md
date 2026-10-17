# platform：D 的平台区域

D 维护 identity、asset、moderation，以及同级 common、工程和部署。

- identity：登录、会话、账号状态和权限。
- asset：文件、归属校验、受控读取。
- moderation：举报、下架入口、分类地点、统计、管理日志。

每模块四层：api、application、domain、infrastructure。

管理端下架通过 B 的 RecoveryWorkflowService 处理关联流程，不直接改申请表。

私密文件策略可由 B 提供只读业务实现，D 保留统一许可入口。D 不再编写 AI 任务框架，该范围归 C。
