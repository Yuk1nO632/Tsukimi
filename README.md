# Tsukimi

下一集，继续喜欢。

一个在全栈课程复习中持续迭代的个人追番 Web 项目。正式应用和复习实验分开，整个工作区由同一个 Git 仓库管理。

## 启动正式项目

用 VS Code 打开整个 Tsukimi，打开两个终端。当前机器依赖已经安装，无需每次重新安装。VS Code 终端已自动激活 .venv 时，可以省略激活命令。

终端 1：启动后端。

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

终端 2：启动前端。

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000。后端接口文档：http://127.0.0.1:8000/docs。停止服务时，在对应终端按 Ctrl+C。若旧的前端服务还开着，先停止再启动，以加载 API 转发配置。

新环境安装：前端运行 npm.cmd ci；后端运行 python -m venv .venv，再运行 .\.venv\Scripts\python.exe -m pip install -r requirements.txt。测试依赖见 requirements-dev.txt。

## 当前已实现

- 参考 B 站番剧频道的首页与播放页，真实当季新番轮播和九部真实番剧资料。
- 分类、搜索、详情、首播日历、个人片单及手机布局。
- 稀饭动漫单源播放：真实 video、暂停、进度拖动、音量、倍速、宽屏、全屏，支持 MP4 和 HLS 线路。
- 来源搜索、人工确认匹配、切集、换线和加载失败重试；另有标注清楚的本地测试短片。
- FastAPI 收藏接口与 SQLite 数据库，收藏和取消收藏在刷新、后端重启后仍然保留。
- 匿名 Cookie 区分浏览器；前端提供读取中、保存中、失败重试，后端确认保存成功后才更新收藏状态。

收藏保存在 project/backend/data/tsukimi.db，Cookie 有效期为首次建立会话起 30 天。请持续使用同一浏览器和地址；清除 Cookie、隐私窗口或更换浏览器会建立另一份片单，目前没有账号与跨设备同步。

首页搜索范围是已同步的九部动画，不是全站联网搜索。评分、日期是资料快照，不代表本站热度或当前更新排期。已核验《葬送的芙莉莲》第一、二集的真实播放与主/备用线路。其他番剧可在播放页搜索并手动匹配稀饭来源；是否可用取决于来源站。观看进度、自动续播与弹幕尚未接入。

## 更新资料与执行检查

在 project/frontend 运行 npm.cmd run sync:catalog，资料写入 project/catalog/catalog.json，封面保存到 frontend/public/covers。更新后重启后端以重新读取片单；当前季度推荐需要人工维护。

前端构建：在 frontend 中运行 npm.cmd run build。

后端测试：在 backend 中先运行 .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt，再运行 .\.venv\Scripts\python.exe -m unittest -v。测试使用临时数据库，不修改个人收藏。

## 工作区结构

```text
Tsukimi/
  .git/                 统一 Git 仓库
  docs/                 计划、阶段指南和学习记录
  experiments/          原生页面与 React 复习实验
  project/
    frontend/           Next.js 前端
    backend/            FastAPI 接口与 SQLite 存储
    catalog/            前后端共用的本地番剧资料
```

数据库、虚拟环境、node_modules、缓存与测试截图不提交 Git。正式功能持续在 project 内迭代，每个验证通过的阶段保存 Git 版本。

## 阅读入口

- [本轮：真实播放器与稀饭来源](docs/06-真实播放器与稀饭来源.md)
- [收藏接口、Cookie 与 SQLite](docs/05-收藏接口与数据库.md)
- [频道 UI、播放页与真实资料](docs/04-番剧频道与真实资料.md)
- [素材来源](docs/素材说明.md)
- [Git 使用约定](docs/Git使用约定.md)
- [复习与项目计划](docs/复习与项目计划.md)
- [学习记录](docs/学习记录.md)

## 保留的复习实验

实验 01：根目录运行 python -m http.server 5173 --bind 127.0.0.1 --directory experiments/01-browser-basics，访问 http://127.0.0.1:5173；start.ps1 也仍用于这个实验。

实验 02：进入 experiments/02-react-state 运行 npm.cmd run dev，访问 http://127.0.0.1:5174。

- [实验 01 指南](docs/01-浏览器与页面状态.md)
- [实验 02 指南](docs/02-React组件与状态.md)
