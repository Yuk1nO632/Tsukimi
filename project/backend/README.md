# Tsukimi 后端

基于 FastAPI 和 SQLite，提供番剧资料、账号、片单、观看进度以及 AniCh / 稀饭双来源播放接口。完整项目安装与前端启动见 [仓库 README](../../README.md)。

## 本地启动

以下命令在 `project/backend` 目录的 Windows PowerShell 中执行。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Linux / Ubuntu 对应命令如下。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

依赖安装完成后，日常启动执行对应的 Uvicorn 命令即可。首次启动会初始化数据库并载入本地精选资料。

- [交互式接口文档](http://127.0.0.1:8000/docs)
- [健康检查](http://127.0.0.1:8000/api/health)

## 模块职责

| 文件 | 职责 |
| --- | --- |
| `main.py` | 创建应用、读取配置、注册路由和处理请求来源 |
| `database.py` | SQLite 建表、兼容迁移与数据查询 |
| `sessions.py` | 浏览器 Cookie、会话有效期与数据归属 |
| `accounts.py` | 注册登录、密码与密保、匿名记录导入 |
| `progress.py` | 观看进度读取、保存、删除与版本冲突处理 |
| `catalog.py` | Bangumi 资料搜索、详情、日历与缓存 |
| `playback.py` | 来源搜索、手动关联、来源优先级与逐集解析 |
| `anich.py`、`anich_protocol.py` | AniCh 适配、候选校验和协议解析 |
| `xifan.py` | 稀饭备用来源适配 |
| `create_admin.py`、`transfer_admin.py` | 管理员创建与单账号迁移工具 |

## 接口概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 检查后端响应 |
| GET | `/api/catalog` | 搜索、筛选、排序和分页 |
| GET | `/api/catalog/calendar` | 获取当前放送计划 |
| GET | `/api/catalog/{anime_id}` | 获取详情，`summary=true` 可读取已有摘要 |
| GET | `/api/account` | 读取账号状态、建立匿名会话并返回 scope |
| POST | `/api/account/register`、`/api/account/login`、`/api/account/logout` | 注册、登录与退出 |
| POST | `/api/account/recovery`、`/api/account/reset-password` | 获取密保挑战与重置密码 |
| POST | `/api/account/password`、`/api/account/security-questions` | 修改密码与密保 |
| POST | `/api/account/import` | 确认导入或跳过匿名记录 |
| GET | `/api/collection` | 读取片单 |
| PUT / DELETE | `/api/collection/{anime_id}` | 设置状态和移出片单 |
| GET | `/api/progress`、`/api/progress/{anime_id}` | 列出观看记录或读取单部进度 |
| PUT / DELETE | `/api/progress/{anime_id}` | 保存或清空续播记录 |
| GET | `/api/sources/{source_provider}/search` | 搜索指定来源的作品 |
| PUT | `/api/sources/{source_provider}/bindings/{anime_id}` | 保存人工确认的来源关联 |
| GET | `/api/playback/{anime_id}` | 选择剧集与来源，解析临时播放地址 |

片单状态使用 `wish`、`watching`、`completed`，分别对应想看、在看、看完。旧 `/api/favorites` 接口继续提供收藏 ID 的兼容读写。

需要身份的写操作由 Cookie 确定归属，片单与进度等前端请求还带上 `X-Tsukimi-Scope` 校验当前身份。进度保存与删除还携带 `scope`、`revision` 和 `operation_id`，用于身份检查、并发版本检查及重试识别。具体请求字段和响应结构可通过接口文档及对应路由模块查看。

## 配置与持久化

启动时读取本目录的 `.env`，示例见 [.env.example](.env.example)。

| 环境变量 | 默认值或用途 |
| --- | --- |
| `TSUKIMI_DATABASE` | 默认本目录下的 `data/tsukimi.db` |
| `TSUKIMI_ALLOWED_ORIGINS` | 逗号分隔的浏览器来源，默认包含本机 3000 与 8000 地址 |
| `TSUKIMI_COOKIE_SECURE` | 本地 HTTP 默认为 `0`，HTTPS 部署设为 `1` |
| `TSUKIMI_ANICH_API` | 默认 `https://anich.sends.eu.org`，可配置 AniCh 服务地址 |
| `TSUKIMI_XIFAN_PUBLIC_KEY` | 可覆盖稀饭适配器使用的公开接口标识，默认采用适配器内置值 |

SQLite 保存会话、账号、片单、进度、来源偏好及资料缓存。兼容迁移在初始化时执行，特定旧表升级会先创建相应备份。常规发布另按 [部署指南](../../docs/10-部署与管理员迁移.md) 保存数据库快照。

## 资料与播放来源

资料 ID 使用 Bangumi 标识，播放作品与线路编号分别归属所选来源。AniCh 与稀饭的编号通过来源标记隔离，自动匹配会核对作品身份，页面提供人工校正入口。解析过程支持备用来源补位和用户优先级选择。

后端返回候选线路与临时媒体地址，播放器直接连接 CDN。资料缓存、账号偏好和观看进度分别保存，签名播放地址按播放请求重新解析。实际来源与线路可用性由外部服务响应决定。

## 测试与工具

在本目录执行后端测试。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest -v
```

Linux 使用 `.venv/bin/python` 替换 Python 路径。测试通过临时数据库和模拟上游覆盖账号、片单、观看进度、匹配逻辑、迁移与并发请求。

管理员创建同样在本目录执行，密码在终端交互输入。

```powershell
.\.venv\Scripts\python.exe create_admin.py --username your_admin
```

管理员角色用于账号身份区分，管理后台列入后续规划。已有管理员的导出、传输与导入操作见 [管理员迁移指南](../../docs/10-部署与管理员迁移.md#d-管理员为什么需要单独迁移)。

- [资料库、追番与双来源复习](../../docs/07-联网资料与追番片单.md)
- [账号、进度与版本冲突复习](../../docs/08-观看进度与邮箱账号.md)
