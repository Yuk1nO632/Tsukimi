# Tsukimi

下一集，继续喜欢。

一个在全栈课程复习中持续迭代的个人追番 Web 项目。正式应用和学习实验分开，整个工作区由同一个 Git 仓库管理。

## 启动正式项目

用 VS Code 打开整个 Tsukimi，在终端运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000。结束时按 `Ctrl+C`。当前依赖已安装，新环境先运行 `npm.cmd ci`。如果旧的开发服务还开着，先停止并重新启动，确保加载本轮路由和样式。

## 当前已实现

- 参考 B 站番剧频道的首页：大幅主题横幅、缩略导航、番剧封面、分类筛选、首播日历与个人片单。
- 真实番剧资料：通过 Bangumi API 同步六部动画的名称、简介、封面、集数、标签和评分，保留本地资料缓存。
- 首页搜索、收藏、详情页、独立播放页，以及跨页面共享收藏状态。
- 播放页选集与 URL 高亮、上一集/下一集、宽屏和全屏布局。
- 桌面与手机布局、空状态和 404 页面。

当前播放器尚未接入视频来源，播放和弹幕明确显示未开放；选集导航和界面操作已可用。收藏仍在浏览器内存中，完整刷新会归零，下一阶段用 FastAPI + SQLite 持久保存。

当前搜索范围是已同步的六部真实动画，不是对全部 Bangumi 条目的在线搜索。评分、日期都是资料缓存，不代表本站播放热度或当前更新排期。

## 更新真实资料

在 `project/frontend` 中运行：

```powershell
npm.cmd run sync:catalog
```

同步脚本通过系统网络访问 Bangumi 公开 API，下载选定条目的资料和封面。依赖网络的更新操作与日常页面访问分开；已有缓存可以让开发页面在接口暂时不可用时继续打开。

## 工作区结构

```text
Tsukimi/
  .git/                 统一 Git 仓库
  docs/                 计划、阶段说明、学习记录和素材说明
  experiments/          原生页面与 React 的独立复习实验
  project/
    frontend/           正式 Next.js 前端
```

`project/backend/` 在开始 FastAPI 开发时创建。正式功能直接在 project 内迭代，每个完成并验证的阶段提交 Git。

## 阅读入口

- [本轮：频道 UI、播放页与真实资料](docs/04-番剧频道与真实资料.md)
- [素材来源与原创插画提示词](docs/素材说明与提示词.md)
- [Git 使用约定](docs/Git使用约定.md)
- [复习与项目计划](docs/复习与项目计划.md)
- [学习记录](docs/学习记录.md)
- [第一阶段：Next.js 首页与详情](docs/03-正式项目与Next路由.md)

## 保留的复习实验

实验 01：进入根目录运行 `python -m http.server 5173 --bind 127.0.0.1 --directory experiments/01-browser-basics`，访问 http://127.0.0.1:5173；根目录 start.ps1 也仍用于这个实验。

实验 02：进入 `experiments/02-react-state` 运行 `npm.cmd run dev`，访问 http://127.0.0.1:5174。

- [实验 01 指南](docs/01-浏览器与页面状态.md)
- [实验 02 指南](docs/02-React组件与状态.md)
