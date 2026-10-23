# Tsukimi

月下片刻，故事未完。

一个通过全栈课程复习逐步搭建的个人追番 Web 项目。原项目名为 Animora，现统一使用 **Tsukimi**。

## 当前阶段

- 学习进度：已学到模块 6.6；计划于 2026-10-23 学习完成 6.6 和 7.1，是否完成以学习记录为准。
- 学习方式：先做小实验、观察结果，再把知识迁移到项目。
- 实验 01：HTML、CSS、JavaScript 与页面状态，已阅读并讨论相关概念。
- 当前进入实验 02：React 组件、props 与 state；代码已准备，按指南动手验证。
- 两个实验独立保留，使用虚构条目，不连接外部资料或视频服务。

## 当前实验：React 组件与状态

在 VS Code 打开整个项目，在终端运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\experiments\02-react-state
npm.cmd run dev
```

打开 <http://127.0.0.1:5174>，结束时在对应终端按 `Ctrl+C`。

当前环境已安装依赖。新环境或依赖目录不存在时，先运行 `npm.cmd install`。使用已有锁文件恢复依赖时可以运行 `npm.cmd ci`。本实验的运行环境要求见 `package.json`，当前电脑的 Node.js 版本满足要求。

先看 [实验 02 操作指南](docs/02-React组件与状态.md)，重点阅读 `App.jsx` 与 `components/AnimeCard.jsx`，不用逐行阅读依赖目录。

## 对照实验：原生页面

在另一个终端中运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi
python -m http.server 5173 --bind 127.0.0.1 --directory experiments/01-browser-basics
```

打开 <http://127.0.0.1:5173>。也可以运行根目录的 `start.ps1` 启动实验 01；如果脚本执行受限，用上面的 Python 命令，无需修改系统策略。

两个开发服务器都只监听本机，均不保存收藏；Vite 为实验 02 转换 JSX 和提供热更新，Python 为实验 01 提供静态文件。FastAPI 业务后端和数据库会在后续实验加入。

端口被占用时先检查对应实验是否已在运行。React 实验可运行 `npm.cmd run dev -- --port 5175`，再打开终端打印的地址。

## 学习资料

1. [复习与项目计划](docs/复习与项目计划.md)
2. [实验 01：浏览器与页面状态](docs/01-浏览器与页面状态.md)
3. [实验 02：React 组件与状态](docs/02-React组件与状态.md)
4. [学习记录](docs/学习记录.md)

实验 01 使用 Python 标准库；实验 02 使用 npm 管理的 React 与 Vite。原生版本和 React 版本的收藏都仍会在完整刷新后重置。
