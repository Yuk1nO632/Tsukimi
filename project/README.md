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

- 联网资料库、首页当季分区、独立搜索/索引/日历/追番页与动态详情已实现；本地九部作为精选与资料回退。
- 当前片单通过 /api/collection 读写想看/在看/看完，旧 /api/favorites 继续兼容。匿名 Cookie 和 SQLite 保留。
- 页面刷新与后端重启后记录保留；清除 Cookie 或匿名会话超过 30 天不保证找回旧片单。
- 已固定使用 AniCh 聚合来源与 MP4/HLS 播放；观看进度、弹幕、账号与跨设备同步尚未接入。
- 资料同步在 frontend 运行 npm.cmd run sync:catalog，输出 catalog/catalog.json；同步后重启后端。

详细安装、复习步骤与验收见 ../docs/05-收藏接口与数据库.md；数据库文件 backend/data/tsukimi.db 不提交 Git。

当前整站复习指南：../docs/07-联网资料与追番片单.md。

播放指南：../docs/06-真实播放器与稀饭来源.md。首个已核验样本为 /watch/bgm-400602?episode=1；作品进入后自动匹配；不能唯一确认时再手动选择。

2026-10-28：顶部提供可点击搜索建议，详情移除来源卡片，剧集进入后自动匹配并加载。来源确认按当前匿名会话记忆；公开列表短时缓存，私人片单仍实时读取。复习见指南 07 E。


2026-11-01：正式播放已切换 AniCh 聚合接口，旧来源 ID 与链接参数隔离；失败时可一键换线。运行依赖和启动命令不变，后端测试共 51 项。

补充清理：旧稀饭适配器与专用映射/测试已删除，通用错误移到 source_errors.py。当前为 37 项后端测试、5 项前端检测测试；旧阶段测试数仅保留在历史记录。

性能更新：详情先显示已有资料，再补齐制作信息；搜索不会覆盖完整详情。四个主导航在生产环境完整预取。日常浏览可在停止 dev 后运行 npm.cmd run preview，代码修改后重新运行。当前后端 40 项测试。
