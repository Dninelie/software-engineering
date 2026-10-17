# 建表脚本

第一版六张表：app_user、post、file_asset、claim、clue、report。

B 写 post/claim/clue，D 写用户/文件/举报，D 合并为本目录 schema.sql，另给虚构演示数据。当前没有 SQL 文件，不能视为数据库已创建。

SQLAlchemy models.py 与 SQL 必须保持字段、类型、默认值、索引和外键一致。B/D 共用 common/database.py 的 Base；由 D 明确注册两个 models 模块。

初始脚本按外键依赖创建表；已有库变更提供显式 ALTER。第一版不引入 Alembic，不在应用启动时删库重建。

不建任务、通知、向量、匹配缓存或独立会话表；不使用旧归档脚本。
