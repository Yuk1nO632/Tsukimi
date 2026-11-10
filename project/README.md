# Tsukimi 正式应用

本目录包含 Next.js 前端、FastAPI 后端与本地精选资料。安装、双终端启动、配置、测试和部署入口统一收录在 [仓库 README](../README.md)。

## 目录职责

| 目录 | 内容 |
| --- | --- |
| `frontend/app` | 首页、索引、日历、详情、播放、追番与账号路由 |
| `frontend/components` | 频道布局、播放器、来源匹配、片单与账号交互 |
| `frontend/lib` | API 请求、播放来源参数、观看进度与前端状态逻辑 |
| `frontend/tests` | 推荐、线路检测、双来源请求与进度处理测试 |
| `backend` | HTTP 接口、账号会话、SQLite 持久化、Bangumi 资料与 AniCh / 稀饭适配 |
| `catalog/catalog.json` | 初始精选番剧资料，用于启动载入和页面精选 |

## 页面与数据流

浏览器在前端完成搜索、收藏、选集和播放操作，通过 `/api` 访问后端。后端按会话与账号归属读取、保存 SQLite 数据，并访问外部资料与播放来源服务。浏览器取得临时播放地址后，直接读取视频 CDN。

本地开发由 Next.js 将 `/api` 转发到默认的 `127.0.0.1:8000`。生产环境通过 Nginx 提供统一域名入口，systemd 管理两个应用进程。

## 常用维护

- 依赖安装与启动，见 [快速开始](../README.md#快速开始)。
- 后端接口与模块说明，见 [后端 README](backend/README.md)。
- 本地精选资料同步，在 Windows PowerShell 的前端目录运行 `npm.cmd run sync:catalog`，脚本使用 PowerShell，写入 `catalog/catalog.json` 与前端封面目录，同步完成后重启后端读取资料。
- 账号、片单和观看记录默认写入 `backend/data/tsukimi.db`，生产数据路径通过 `TSUKIMI_DATABASE` 指定。
- 管理员创建在后端目录运行 `create_admin.py --username 账号名`，使用虚拟环境 Python 调用，密码由终端交互输入。
- 管理员迁移、数据库备份和版本发布，见 [部署复习指南](../docs/10-部署与管理员迁移.md)。

## 按功能阅读

- [搜索、筛选、日历与追番](../docs/07-联网资料与追番片单.md)
- [观看进度、删除记录与账号同步](../docs/08-观看进度与邮箱账号.md)
- [完整业务流程验收](../docs/09-上线前核心流程联测.md)

学习实验位于仓库根目录的 `experiments`，阶段记录位于 `docs`。
