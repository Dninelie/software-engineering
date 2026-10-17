# 机器可读合同

| 文件 | 用途 |
|---|---|
| [openapi.json](openapi.json) | OpenAPI 3.0.3，固定方法、路径、Schema、权限标记和负责人 |
| [module-dependencies.json](module-dependencies.json) | 计划中的服务依赖、目录与表归属，用于检查循环和越界 |

接口字段以 OpenAPI 为准；业务条件、锁和事务以 [对接约定](../12-integration-contracts.md) 为准。OpenAPI 的 x-owner、x-access、x-semantic-validation 是项目自定义说明，不代表框架自动实施。

图描述计划实现，不是从已编译代码提取。Java 类实现后须增加实际包依赖、Spring 启动、事务和权限测试。

从项目根目录运行 `node scripts/verify-design.mjs`。脚本不安装依赖，只做静态结构检查，不冒充完整标准验证器或运行时验收。

维护责任：B 业务接口、C AI/任务接口、D 平台接口与公共结构；D 主维护检查脚本，B/C 提交相关检查，A 反馈客户端需求。
