# Tsukimi

月下片刻，故事未完。

通过全栈课程复习逐步搭建的个人追番 Web 项目。原项目名为 Animora，现统一使用 **Tsukimi**。

## 从这里开始：正式项目

用 VS Code 打开整个 `C:\Users\lx\Desktop\Tsukimi` 工作区，在终端运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000，结束时按 `Ctrl+C`。当前电脑已经安装依赖；新环境进入同一目录运行 `npm.cmd ci` 后启动。Windows 使用 `npm.cmd` 可以避免 npm.ps1 的执行策略问题。

当前正式版本包含首页、关键词搜索、收藏筛选、详情页和友好的未找到页面。数据为三部虚构演示番剧。收藏在站内导航中共享，完整刷新会重置；真实资料、FastAPI、SQLite 和视频播放将在后续阶段接入。

## 工作区结构

```text
Tsukimi/
  .git/                 一个本地 Git 仓库，记录整个工作区
  docs/                 计划、阶段说明和学习记录
  experiments/          独立复习小实验
    01-browser-basics/  原生 HTML/CSS/JavaScript
    02-react-state/     Vite + React
  project/              持续迭代的正式项目
    frontend/           Next.js 前端
```

`project/backend/` 在下一阶段开始 FastAPI 开发时创建。以后正式功能直接在 `project/` 中修改，每个完成并验证的阶段提交 Git。

## 本轮重点

- [正式项目第一阶段：Next.js 首页与详情](docs/03-正式项目与Next路由.md)
- [Git 记录与回退](docs/Git使用约定.md)
- [复习与项目计划](docs/复习与项目计划.md)
- [学习记录](docs/学习记录.md)

## 复习实验入口

实验 01：

```powershell
cd C:\Users\lx\Desktop\Tsukimi
python -m http.server 5173 --bind 127.0.0.1 --directory experiments/01-browser-basics
```

实验 02：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\experiments\02-react-state
npm.cmd run dev
```

实验 01 地址为 http://127.0.0.1:5173，实验 02 地址为 http://127.0.0.1:5174。根目录的 `start.ps1` 仍用于实验 01，正式前端请用上面的 `project/frontend` 命令。

- [实验 01 指南](docs/01-浏览器与页面状态.md)
- [实验 02 指南](docs/02-React组件与状态.md)

这些本地服务只监听本机。正式项目由 Next.js 提供开发服务，后续的 FastAPI 才处理业务 API；第一版没有保存账号或视频文件。
