# business：B 的业务区域

B 维护 post、recovery、notification，以及对应 DTO、Mapper、迁移和测试。

- post：正式物品数据、查询和信息状态。
- recovery：线索、证明、申请、交接和归还事务。
- notification：站内通知和去重。

每模块四层：api、application、domain、infrastructure。

通过 C 的 JobService 入队；通过 D 的身份和文件服务处理基础能力。向 C 提供只读查询和通知服务，向 D 提供下架工作流。

不调用外部模型，不直接修改 intelligence/platform 的表。JobService 入队参与当前事务；PostQueryService 必须保持只读，不依赖入队。
