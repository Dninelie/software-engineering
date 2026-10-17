# 验收资料

acceptance/ 保存人工与真机验收记录；ai-samples/ 保存约 20 组 AI/匹配样例。

Python 自动化测试放 backend/tests/，分别由 B/C/D 维护 business、intelligence、platform；A 负责页面与真机验证。统一使用 pytest，接口测试使用 FastAPI TestClient。

规则函数可用固定输入独立测试；行锁和并发认领必须使用专用 MySQL 测试库，不用 SQLite 结果代替。

当前以 [18 个核心用例](../docs/06-development-and-testing.md) 为准。模板和文档检查不表示实际业务验收通过。
