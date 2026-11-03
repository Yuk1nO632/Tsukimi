# Tsukimi

番剧资料、放送日历与个人追番片单。

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

- 参考 B 站频道结构的暖白与玫瑰粉界面，首页使用深色真实海报轮播；首页自动读取当季资料，保留本地经典精选。
- 联网搜索番名、原名和别名，按年份/季度/类型筛选，支持排序与分页；完整详情、当前放送日历、独立追番页和手机布局。
- AniCh 聚合播放：真实 video、暂停、进度拖动、音量、倍速、宽屏、全屏，支持 MP4 和 HLS 线路。
- 来源自动匹配、一次确认后按浏览器记忆、切集、换线和加载失败重试；另有标注清楚的本地测试短片。
- FastAPI 片单接口与 SQLite，管理想看/在看/看完，刷新和后端重启后仍保留；旧收藏自动迁移为想看。
- 匿名 Cookie 区分浏览器；前端提供读取中、保存中、失败重试，后端确认保存成功后才更新收藏状态。

收藏保存在 project/backend/data/tsukimi.db，Cookie 有效期为首次建立会话起 30 天。请持续使用同一浏览器和地址；清除 Cookie、隐私窗口或更换浏览器会建立另一份片单，目前没有账号与跨设备同步。

顶部搜索已接入 Bangumi 联网资料，输入可显示带海报的联想，点击直达详情；剧集在播放页自动匹配来源，不限本地九部。放送日历展示当前在播安排，实际资源更新以播放来源为准；评分与热度属于资料站。当前已实测 AniCh 芙莉莲第一、二集、MP4/HLS 与换线，以及《伪恋》第一、二集；旧稀饭适配器、预置映射和专用接口已删除，需要对照时查看 Git f8dcedb。观看进度、自动续播、弹幕和账号同步尚未接入。

## 更新资料与执行检查

在 project/frontend 运行 npm.cmd run sync:catalog，资料写入 project/catalog/catalog.json，封面保存到 frontend/public/covers。更新后重启后端以重新读取片单；本地精选仍通过该脚本维护；当前首页的新番分区和轮播改由联网查询，不依赖手工更新推荐 ID。

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

- [待复习：联网资料与追番片单](docs/07-联网资料与追番片单.md)
- [AniCh 聚合接口验证与适配记录](docs/Anich聚合接口可行性验证.md)
- [真实播放器与稀饭来源](docs/06-真实播放器与稀饭来源.md)
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

线路响应：播放页展开“线路响应”，点击“检测线路”查看首包耗时，可按耗时排序或点击结果换线；不显示文件大小。不可测不等于不能播放。前端检测测试：在 frontend 执行 node --test tests/line-probe.test.mjs。


## 日常试用的生产预览

后端保持运行。前端终端先按 Ctrl+C 停止 dev，再运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run preview
```

预览仍在 http://127.0.0.1:3000，使用独立 .next-preview 构建目录，不覆盖开发构建。首次运行会先构建；之后按 Ctrl+C 停止。修改代码后需重新运行 preview；边改边看的学习场景继续用 npm.cmd run dev。脚本发现 3000 被占用会直接提示，不关闭已有服务。

当前后端 40 项测试、前端线路检测 5 项测试通过。页面加载排查与说明见指南 07 H。
