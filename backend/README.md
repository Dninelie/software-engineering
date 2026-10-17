# Python 后端

采用 Python 3.12、FastAPI、Pydantic 2、SQLAlchemy 2 同步 Session、PyMySQL、MySQL。外部请求使用 HTTPX 同步客户端，由 Uvicorn 运行。

当前仅有目录骨架和开发设计，没有 main.py、requirements 或业务实现，暂不能运行。下面是初始化后的目标，不是现有启动能力。

## 目录与所有者

```text
app/
├── main.py           D：应用装配
├── common/           D：配置、会话、异常、公共类型
├── business/         B：发布、线索、认领
├── intelligence/     C：AI、匹配规则
└── platform/         D：登录、文件、字典、举报、管理
sql/                  B/D：schema.sql 和演示数据
tests/
├── business/
├── intelligence/
└── platform/
```

各 Python 包初始化时建立 __init__.py。不按人各建一套 FastAPI 应用；main.py 统一 include_router，业务统一前缀 /api/v1。

## 待建立的依赖文件

D 统一维护 requirements.txt 和 requirements-dev.txt，固定实际验证过的精确版本。

| 文件 | 拟包含 |
|---|---|
| requirements.txt | fastapi、uvicorn、pydantic、pydantic-settings、sqlalchemy、pymysql、httpx、python-multipart、Pillow、pwdlib[argon2]、tzdata |
| requirements-dev.txt | 引入 requirements.txt，再加入 pytest |

MySQL 若使用需要 RSA 的认证插件，采用 PyMySQL 的相应依赖 extra；由 D 根据实际认证配置验证。不要为四个人分别引入不同数据库驱动或 ORM。

## 初始化完成后的启动流程

1. 建立 Python 3.12 虚拟环境，安装 requirements-dev.txt。
2. 复制 backend/.env.example 到 backend/.env，填数据库、微信和模型配置。
3. 创建数据库，执行 sql/schema.sql，使用 D 提供的 scripts/create_admin.py 初始化管理员。
4. 从 backend 目录执行 python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload。
5. 访问 http://127.0.0.1:8080/docs 联调公开列表、登录、上传和业务接口。
6. 执行 python -m pytest；涉及锁与并发的测试使用专用 MySQL 测试库。

这些文件/脚本尚未实现。D 建立 .env 加载：pydantic-settings 从 backend/.env 读取，系统环境变量覆盖文件；不得假定框架自动识别所有变量。正式部署不加 --reload，绑定地址由部署配置决定。

STORAGE_ROOT 相对 backend 工作目录解析；时区用 CAMPUS_TIME_ZONE。配置缺失须明确报错；无 AI 密钥时模型接口返回 AI_UNAVAILABLE，基础业务仍可用。

参见 [架构](../ARCHITECTURE.md)、[分工](../docs/02-modules-and-team.md)、[开发交接](../docs/06-development-and-testing.md)。
