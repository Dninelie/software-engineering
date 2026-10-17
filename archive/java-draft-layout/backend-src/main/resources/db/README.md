# 建表脚本

第一版六张表：app_user、post、file_asset、claim、clue、report。

B 写 post/claim/clue，D 写用户/文件/举报，D 合并为 schema.sql。当前还没有 SQL 文件，不能视为数据库已创建。

不建任务、通知、向量、匹配缓存和独立会话表；不使用旧归档迁移。
