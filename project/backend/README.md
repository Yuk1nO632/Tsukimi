# Tsukimi 后端

## 文件职责

- main.py：HTTP 路由、匿名 Cookie、会话查找、番剧 ID 校验。
- database.py：SQLite 建表与参数化查询，每次操作关闭连接。
- test_favorites.py：用临时数据库验证持久化、隔离、重复请求和错误响应。
- data/tsukimi.db：个人运行数据，第一次启动时创建，Git 忽略。

## 安装与启动（PowerShell）

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

当前机器已安装依赖，平时只运行最后一条。直接指定虚拟环境里的 Python，无需执行 Activate.ps1。

接口文档：http://127.0.0.1:8000/docs。

## 接口

| 方法 | 地址 | 作用 |
| --- | --- | --- |
| GET | /api/health | 检查进程可访问 |
| GET | /api/favorites | 建立或读取匿名会话，返回收藏 ID |
| PUT | /api/favorites/{anime_id} | 收藏，重复调用不会重复添加 |
| DELETE | /api/favorites/{anime_id} | 取消收藏，重复调用结果一致 |

先执行 GET，再执行 PUT 或 DELETE。返回结构为 {"favorite_ids":["bgm-568244"]}。无有效会话写入返回 401，未收录条目返回 404，数据库暂不可用返回 503。

## 配置

- TSUKIMI_DATABASE：数据库路径，默认当前 backend/data/tsukimi.db。
- TSUKIMI_ALLOWED_ORIGINS：逗号分隔的允许写入来源；默认包含本机 3000 前端与 8000 文档页。换开发端口时同步修改。
- TSUKIMI_COOKIE_SECURE=1：HTTPS 部署时启用；本地 HTTP 开发默认关闭。

当前浏览器请求先到 Next.js 的同源 /api，再转发到 FastAPI，不需要额外开放跨域 CORS。当前服务仅绑定 127.0.0.1，公网部署留到部署课程阶段。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest -v
```

测试不修改个人数据库。当前依赖版本的 TestClient 会提示旧 httpx 兼容层将弃用，该提示不影响测试执行。

## 稀饭动漫单源播放

playback.py 提供 GET /api/sources/xifan/search?q=关键词 与 GET /api/playback/{anime_id}?episode=1。后者可附带 source_anime_id 和 line_id 进行显式匹配与线路选择。

xifan.py 请求稀饭 Next 的公开搜索、选集和临时播放地址接口；metadata 缓存 5 分钟，播放地址在每次解析时重新申请。视频由浏览器直接连接 CDN，后端不转发视频字节。当前只允许核对过的两个 CDN 主机。

默认匹配保存在 ../catalog/xifan-bindings.json，目前仅预置芙莉莲对应来源条目 26。其余作品由界面搜索和人工确认；query source 是来源作品 ID，不是 Bangumi ID。

当前测试共 39 项，来源相关测试使用 MockTransport，无需访问上游。真实端到端播放还需网络，详见根目录 docs/06-真实播放器与稀饭来源.md。

## 联网资料与片单状态（2026-10-27）

- GET /api/catalog：q、year、season、genre、sort、page、limit；搜索仅查询动画，排序为 match/heat/score/rank。
- GET /api/catalog/{anime_id}：读取完整详情，可从带提示的缓存回退；不是仅允许原来九个 ID。
- GET /api/catalog/calendar：当前每周放送计划，星期与追番筛选由前端执行，不保证来源已上架新一集。
- GET /api/collection：建立/读取原匿名会话，返回 items，其中含 anime、status、updated_at。
- PUT /api/collection/{anime_id}：JSON 为 {"status":"wish"}，允许 wish/watching/completed。
- DELETE /api/collection/{anime_id}：移出片单，返回更新后的完整片单。

旧 favorites 表增加 status 与 updated_at，既有收藏默认 wish；catalog_cache 存公开资料快照，片单重启后不依赖进程内目录。旧接口保持兼容，其 PUT 不会覆盖已经设置的追番状态。非法状态 422、失效会话 401、跨来源写入 403、资料不存在 404、数据库故障 503。

catalog.py 使用固定 Bangumi 主机、公开只读接口、超时与有限大小的上游响应缓存。搜索/日历响应缓存约 10 分钟；详情快照约 24 小时，错误回退明确提示。临时视频 URL 不进入资料缓存或数据库。测试使用临时数据库和模拟上游；当前 TestClient 的弃用提示保持原状，不为本轮改动替换测试依赖。

## 自动匹配与来源偏好（2026-10-28）

GET /api/playback/{anime_id} 未指定来源时，依次使用当前浏览器记住的选择、预置关系、一天内自动匹配缓存或新搜索。匹配要求规范化精确名称及年份/集数证据；明确季数冲突不自动替代。无法唯一确定时返回 unmatched 与 candidates，让界面直接提供候选。

PUT /api/sources/xifan/bindings/{anime_id} 的 JSON 为 {"source_anime_id":360}，需要原会话与同源写入校验，验证来源后写入 source_bindings。自动关系写入 auto_source_bindings。两者均只存编号，resolve 每次仍申请临时视频地址。显式 URL 选择只控制当前请求，不覆盖记忆。

HTTP 客户端按服务生命周期复用并在关闭时释放；来源搜索短时缓存，搜索资料批量写入 SQLite。已有收藏、片单状态与原数据库继续保留。测试使用模拟上游、临时数据库，当前共 39 项。