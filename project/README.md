# Tsukimi 正式项目

这个目录保存持续迭代的正式应用。`../experiments/` 保存独立复习实验，`../docs/` 保存学习记录和阶段说明；整个工作区共用根目录的 Git 仓库。

## 当前目录

- `frontend/`：Next.js 前端，包含首页、搜索、收藏与番剧详情。
- `backend/`：下一阶段引入 FastAPI 时再创建，当前尚无业务后端。

## 启动前端

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000。依赖已经安装；新电脑先运行 `npm.cmd ci`。完整构建使用 `npm.cmd run build`，构建后可运行 `npm.cmd start`。

当前使用虚构演示资料。收藏由浏览器中的共享 React state 管理，站内 Link 导航会保留，完整刷新会重置。下一阶段接 FastAPI 和 SQLite，实现持久保存。
