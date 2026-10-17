# Python 版部署规划

D 维护。一台服务器运行 FastAPI 后端、MySQL、持久化图片目录和 Vue 管理端静态页。

## 第一版部署范围

- 一个 Uvicorn 应用进程，无独立 AI 服务、worker 或任务队列。
- 生产通过 HTTPS 反向代理访问后端，配置小程序实际 AppID 及 request/uploadFile 等所需域名。
- 图片由后端按当前权限读取，不能用静态服务器直接暴露整个 STORAGE_ROOT。
- 数据库和图片目录持久化并备份，不使用系统临时目录。
- 管理端跨域按实际开发/部署地址配置；小程序真机验证，不只依赖开发工具跳过校验。
- AppSecret、模型 key、数据库密码放服务器环境或 backend/.env，不提交 Git，不放小程序。

## 统一配置来源

变量模板位于 [backend/.env.example](../backend/.env.example)。deploy 不维护第二份同名模板，避免变量分叉。

数据库连接由 common/database.py 用 SQLAlchemy URL.create 组合 DB_HOST/PORT/NAME/USERNAME/PASSWORD，避免密码特殊字符导致手拼 URL 出错。驱动固定 mysql+pymysql，字符集 utf8mb4。

backend/.env 是本地开发加载约定；部署可直接注入环境变量。pydantic-settings 的解析和加载需要 D 在工程初始化时实现，模板不等于配置已经生效。

## 待交付

D 提供固定依赖、main.py、SQL 初始化顺序、管理员创建脚本、反向代理配置及启动命令。B/C 提供本模块检查步骤。

真实微信登录、图片、模型超时和下架返回 404 必须验证；模型不可用时不阻止手动发布和认领。当前没有可执行部署工程，不把本规划当作已经部署成功。
