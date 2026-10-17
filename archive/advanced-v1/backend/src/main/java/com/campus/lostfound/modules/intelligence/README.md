# intelligence：C 的智能区域

C 完整维护 ai、matching、job，包括通用任务框架和处理器。

- ai：图文草稿、模型适配、文本向量。
- matching：候选、评分、理由、版本和降级。
- job：入队、调度、租约、重试、恢复。

每模块四层：api、application、domain、infrastructure。

JobService 只入队，不同步执行模型或依赖具体 handler。处理器通过 B 的只读服务取物品，通过通知服务创建消息。

不覆盖正式特征，不修改认领表，不让小程序直接调用模型。模型请求在事务外，结果保存前验证租约和版本。
