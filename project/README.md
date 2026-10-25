# Tsukimi 正式项目

frontend 是 Next.js 页面，backend 是 FastAPI 接口与 SQLite，catalog 是两端共用的番剧 JSON 资料。复习实验在根目录 experiments，整个工作区共用 Git 仓库。

## 开发启动

终端 1：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

终端 2：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

页面：http://127.0.0.1:3000；接口文档：http://127.0.0.1:8000/docs。

## 当前阶段

- 九部真实资料、首页与详情、独立播放页 UI 已实现。
- 收藏通过 /api/favorites 读写，匿名 Cookie 区分浏览器，SQLite 保存数据。
- 页面刷新与后端重启后记录保留；清除 Cookie 或匿名会话超过 30 天不保证找回旧片单。
- 已接入稀饭动漫单源与 MP4/HLS 播放；观看进度、弹幕、账号与跨设备同步尚未接入。
- 资料同步在 frontend 运行 npm.cmd run sync:catalog，输出 catalog/catalog.json；同步后重启后端。

详细安装、复习步骤与验收见 ../docs/05-收藏接口与数据库.md；数据库文件 backend/data/tsukimi.db 不提交 Git。

当前播放指南：../docs/06-真实播放器与稀饭来源.md。首个已核验样本为 /watch/bgm-400602?episode=1；其他作品可在播放页手动搜索匹配。
