# Tsukimi

一个基于 Next.js、FastAPI 和 SQLite 的追番 Web 应用，集番剧发现、资料检索、片单管理、在线播放和跨设备续播于一体。

番剧资料与放送计划来自 Bangumi，播放来源接入 AniCh 和稀饭动漫。项目在全栈学习过程中持续迭代，正式应用、学习实验和复习文档分别保存在独立目录。

## 功能概览

| 模块 | 当前功能 |
| --- | --- |
| 发现番剧 | 当季轮播、新热视频推荐、人气与高分分区 |
| 资料检索 | 番名、原名及别名搜索，搜索联想，年份、季度、类型筛选与排序 |
| 番剧详情 | 简介、评分、制作资料、选集和来源匹配 |
| 放送日历 | 按星期查看当前放送安排 |
| 我的追番 | 想看、在看、看完，片单搜索与排序 |
| 视频播放 | MP4 / HLS，暂停、拖动、音量、倍速、选集、换线、宽屏、全屏和键盘控制 |
| 观看记录 | 自动保存与恢复进度，账号页查看完整历史和已看完记录，删除单条记录 |
| 外观模式 | 跟随系统、浅色与深色，浏览器记忆选择 |
| 账号同步 | 用户名密码注册登录、三个密保问题找回、修改密码、匿名记录确认导入、跨设备片单与进度同步 |

首页推荐视频进入视口后静音自动播放。正式播放页尝试有声自动播放，浏览器的自动播放策略可能要求一次点击。播放来源支持自动匹配、人工校正与优先级选择，匹配和线路可用性取决于上游返回结果。

邮箱绑定、自动播放下一集、弹幕和管理后台列入后续规划。管理员账号角色与单账号迁移工具已实现。

## 技术结构

| 部分 | 技术 |
| --- | --- |
| 页面与交互 | Next.js App Router、React、CSS |
| 视频播放 | HTML video、hls.js |
| 后端接口 | FastAPI、Uvicorn、HTTPX |
| 数据与账号 | SQLite、Cookie 会话、Argon2 哈希 |
| 生产部署 | Ubuntu、systemd、Nginx、HTTPS |

```text
浏览器
  ├─ 页面与交互 → Next.js
  ├─ /api 请求 → FastAPI → SQLite
  │                         └─ 账号、会话、片单、观看进度和资料缓存
  └─ 视频媒体请求 → 来源 CDN

FastAPI → Bangumi 获取资料
FastAPI → AniCh / 稀饭解析播放来源
```

本地开发通过 Next.js 将 `/api` 转发到 FastAPI。生产部署由 Nginx 统一接收页面与 API 请求，前后端在服务器内分别运行。播放器取得临时地址后，由浏览器连接视频 CDN。

## 快速开始

### 环境准备

本项目已使用 Python 3.12、Node.js 24 和 npm 验证运行，前端声明的最低 Node.js 版本为 20.9。准备 Git，并确保终端能执行 Python、Node.js 和 npm。Ubuntu 创建后端虚拟环境需要安装 `python3-venv`。

克隆仓库。

```bash
git clone https://github.com/Yuk1nO632/Tsukimi.git
cd Tsukimi
```

使用 VS Code 打开仓库，启动两个终端。下面两个终端均从仓库根目录开始执行，选择对应系统的命令。

### Windows PowerShell

终端 1 安装并启动后端。

```powershell
cd project/backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

终端 2 安装并启动前端。

```powershell
cd project/frontend
npm.cmd ci
npm.cmd run dev
```

### Linux / Ubuntu

终端 1 安装并启动后端。

```bash
cd project/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

终端 2 安装并启动前端。

```bash
cd project/frontend
npm ci
npm run dev
```

### 打开应用

- [前端页面](http://127.0.0.1:3000)
- [后端接口文档](http://127.0.0.1:8000/docs)
- [后端健康检查](http://127.0.0.1:8000/api/health)，正常返回 `{"status":"ok"}`

首次启动后端会自动建表并载入本地精选资料。搜索、日历、完整资料获取和来源解析会访问外部服务。

日常启动时，在上述对应目录执行 Uvicorn 与 `npm run dev` 即可。安装环境和依赖发生变化时，再执行相应安装命令。停止本地服务可在其终端按 `Ctrl + C`。

## 配置与数据保存

后端启动时读取 `project/backend/.env`，默认配置适用于上面的本地开发方式。可参考 [配置示例](project/backend/.env.example)。

| 配置项 | 默认行为或用途 |
| --- | --- |
| `TSUKIMI_DATABASE` | 默认保存到 `project/backend/data/tsukimi.db`，可指定其他路径 |
| `TSUKIMI_ALLOWED_ORIGINS` | 逗号分隔的允许来源，默认包含本机 3000 与 8000 地址 |
| `TSUKIMI_COOKIE_SECURE` | 本地 HTTP 默认为 `0`，HTTPS 部署设置为 `1` |
| `TSUKIMI_API_ORIGIN` | 前端 `/api` 转发的后端地址，默认 `http://127.0.0.1:8000` |

前三项由后端读取，最后一项配置在前端进程环境中。前端转发配置发生变化后，开发服务重启，正式部署重新构建并启动。

SQLite 保存账号、会话、片单、观看进度、个人来源选择与资料缓存。匿名记录归属当前浏览器会话，登录同一账号可在多设备读取账号记录。首次登录时，页面提供匿名记录的导入选择。

每部番剧保留最近观看的一集及位置。删除继续观看记录会清空续播位置，追番状态单独保留。不同设备同时修改进度时，通过版本检查提示冲突。

`.env`、数据库、虚拟环境、依赖目录与构建产物由各运行环境管理。数据库备份和账号迁移步骤见 [部署指南](docs/10-部署与管理员迁移.md)。

## 构建、预览与检查

### 正式构建与本地预览

在前端目录运行，后端保持启动。

```bash
npm run build
npm run start
```

默认在 `127.0.0.1:3000` 提供正式构建。Windows PowerShell 可将命令中的 `npm` 写成 `npm.cmd`。

也可以先停止占用 3000 端口的前端，再运行 `npm run preview`。该命令自动构建并启动，使用独立的 `.next-preview` 目录。修改代码后重新运行，以生成最新预览。

生产环境的服务管理、域名、HTTPS、备份与更新流程见 [部署上线与日常维护](docs/10-部署与管理员迁移.md)。

### 后端测试

在后端目录执行。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest -v
```

Linux 使用 `.venv/bin/python` 替换命令中的 Windows Python 路径。测试使用临时数据库与模拟上游验证数据保存、账号隔离、来源匹配、删除和并发写入等行为。

### 前端测试

在前端目录执行。

```bash
node --test tests/*.test.mjs
```

测试覆盖推荐筛选、线路响应检测、来源参数与进度重试处理。最近一次功能验收通过 109 项后端测试、12 项前端测试和正式构建，过程见 [核心流程联测](docs/09-上线前核心流程联测.md) 及 [观看进度指南](docs/08-观看进度与邮箱账号.md)。

## 仓库结构

```text
Tsukimi/
├─ project/
│  ├─ frontend/       页面、组件、播放器与前端资源
│  ├─ backend/        API、账号、数据库与来源适配
│  └─ catalog/        本地精选番剧资料
├─ experiments/      原生页面与 React 学习实验
├─ docs/             复习指南、计划和验证记录
└─ README.md         项目介绍与运行入口
```

- [正式应用结构](project/README.md)
- [后端模块、接口与配置](project/backend/README.md)

## 文档导航

| 想了解什么 | 阅读入口 |
| --- | --- |
| 部署与更新线上版本 | [部署、管理员迁移与日常更新](docs/10-部署与管理员迁移.md) |
| 完整业务流程怎样验收 | [上线前核心流程联测](docs/09-上线前核心流程联测.md) |
| 账号与观看记录怎样保存 | [观看进度与账号密保](docs/08-观看进度与邮箱账号.md) |
| 搜索、片单和双来源怎样配合 | [联网资料与追番片单](docs/07-联网资料与追番片单.md) |
| 播放器的早期实现 | [真实播放器与稀饭来源](docs/06-真实播放器与稀饭来源.md) |
| 从页面到数据库的入门闭环 | [收藏接口、Cookie 与 SQLite](docs/05-收藏接口与数据库.md) |
| 学习实验 | [浏览器与页面状态](docs/01-浏览器与页面状态.md)、[React 组件与状态](docs/02-React组件与状态.md) |
| 项目推进与开发过程 | [复习与项目计划](docs/复习与项目计划.md)、[学习记录](docs/学习记录.md)、[Git 使用约定](docs/Git使用约定.md) |
| 素材与来源说明 | [素材说明](docs/素材说明.md)、[AniCh 接口验证](docs/Anich聚合接口可行性验证.md) |

阶段指南保留对应时期的实操和验证记录。当前启动方式以本 README 为入口，具体实现可沿文档中的模块路径继续阅读。
