# 后端工程

一个 Spring Boot 应用，三个维护区域。Java 21、Spring Security、MyBatis、MySQL、Flyway，具体版本在 P1 锁定。

> 当前为目录骨架，没有 pom.xml、启动类和业务代码，不能构建运行。

## 1. 谁维护哪里

```text
src/main/java/com/campus/lostfound/
├── modules/
│   ├── business/           B
│   │   ├── post/
│   │   ├── recovery/
│   │   └── notification/
│   ├── intelligence/       C
│   │   ├── ai/
│   │   ├── matching/
│   │   └── job/
│   └── platform/           D
│       ├── identity/
│       ├── asset/
│       └── moderation/
└── common/                 D
```

每个模块内保留 api、application、domain、infrastructure。

这是 Java 包和目录边界，不是三个 Maven 工程，不拆三个服务。

## 2. 资源与测试

| 路径 | 维护方式 |
|---|---|
| src/main/resources/mapper/business/ | B 的 SQL 映射 |
| src/main/resources/mapper/intelligence/ | C 的 SQL 映射 |
| src/main/resources/mapper/platform/ | D 的 SQL 映射 |
| src/main/resources/db/migration/ | D 协调编号，B/C/D 写各自迁移 |
| src/test/java/com/campus/lostfound/modules/ | 对应 business、intelligence、platform |
| src/test/java/com/campus/lostfound/common/ | D 的公共基础测试 |

D 管构建、启动和公共配置，B/C 提出依赖需求，不各自创建不同 pom.xml。

## 3. 跨区域调用

使用公开应用服务，不跨区域直接使用 Mapper。业务入队与任务执行分开，只读查询不依赖写用例。

参见 [分工](../docs/02-modules-and-team.md)、[文件清单](../docs/11-file-ownership.md)、[对接约定](../docs/12-integration-contracts.md)。
