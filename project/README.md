# Tsukimi 正式项目

正式应用位于这个目录；复习实验位于工作区根的 experiments，文档位于 docs。整个工作区共用一个 Git 仓库，未来直接在当前应用上迭代。

## 启动

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000。新环境先 `npm.cmd ci`。构建使用 `npm.cmd run build`，构建后可用 `npm.cmd start` 运行。

## 当前阶段

- 番剧频道首页、真实资料详情和独立播放页 UI 已实现。
- 九部真实动画资料来自 Bangumi API，更新命令为 `npm.cmd run sync:catalog`。
- 正式项目只展示真实资料，旧虚构条目已移除；复习实验仍单独保存在 experiments。
- 视频源、弹幕、账号、数据库尚未接入。播放页会明确显示来源状态。
- 收藏由浏览器共享 state 管理，站内导航保留，完整刷新重置。

接下来创建 backend，引入 FastAPI 和 SQLite；联网搜索与后续来源适配再逐步迁移到后端。
