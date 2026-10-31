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

## AniCh 聚合播放（当前正式来源）

- anich.py：固定聚合服务适配、作品关联核对、逐集候选过滤与线路排序。
- anich_protocol.py：有大小/截断检查的 Protobuf wire 读取和官方公开 URL 解码规则；未知字段跳过。
- GET /api/sources/anich/search?q=关键词：来源作品搜索；年份未核实时不伪造。
- PUT /api/sources/anich/bindings/{anime_id}：JSON 为 {"source_anime_id":32339}，需要匿名会话与同源写入校验。
- GET /api/playback/{anime_id}?episode=1：自动匹配、解析临时播放地址。显式选择可附 source_provider=anich、source_anime_id、line_id。
- TSUKIMI_ANICH_API：默认 https://anich.sends.eu.org；无需配置，新终端修改后重启后端生效。

关联优先核对详情 sites 中的 Bangumi ID，没有映射才使用精确名称与年份/集数证据；错误映射不自动选择，人工确认也不能保存已明确关联另一作品的条目。搜索最多两次、每次核对最多四个同名候选详情。

SQLite 沿用 source_bindings/auto_source_bindings，以 anich:bgm-… 作为 AniCh 键；旧未加前缀的稀饭偏好保留但不读取为 AniCh。旧 URL 无 provider 标记的数字不继续当成新来源 ID。收藏、Cookie 和资料 ID 保持原状，无表迁移或数据删除。

详情/剧集缓存 5 分钟、搜索 10 分钟、缓存最多 96 项；VOD 每次请求，不持久化签名地址。线路编号使用来源标识、清晰度、编码、格式的确定性 48 位哈希，不依赖返回下标或签名 URL。按作品说明/季数/集数筛选并将重复镜像合并到同一组，格式未知或资源失效仍可能不能播；前端允许一键换线。显式所选线路缺失时返回 unavailable 和其他候选。

视频直接由浏览器读取 CDN，不代理媒体字节。只接受 HTTPS、公网形式地址，不接受凭证、本机/私网字面 IP、非标准端口；这不等于对所有 CDN 的在线健康检查。优先 H.264、已实测 CDN 和较高清晰度，HLS 继续通过 hls.js 播放。xifan.py 和预置文件仅保留历史回归，不作为当前服务的备用请求。

当前共 51 项后端测试，来源测试使用 MockTransport，无需访问真实上游。真实播放验证见根目录 docs/07-联网资料与追番片单.md 的 F。旧稀饭接口过程可从 Git 9a0dda8 查看。

## 联网资料与片单状态（2026-10-27）

- GET /api/catalog：q、year、season、genre、sort、page、limit；搜索仅查询动画，排序为 match/heat/score/rank。
- GET /api/catalog/{anime_id}：读取完整详情，可从带提示的缓存回退；不是仅允许原来九个 ID。
- GET /api/catalog/calendar：当前每周放送计划，星期与追番筛选由前端执行，不保证来源已上架新一集。
- GET /api/collection：建立/读取原匿名会话，返回 items，其中含 anime、status、updated_at。
- PUT /api/collection/{anime_id}：JSON 为 {"status":"wish"}，允许 wish/watching/completed。
- DELETE /api/collection/{anime_id}：移出片单，返回更新后的完整片单。

旧 favorites 表增加 status 与 updated_at，既有收藏默认 wish；catalog_cache 存公开资料快照，片单重启后不依赖进程内目录。旧接口保持兼容，其 PUT 不会覆盖已经设置的追番状态。非法状态 422、失效会话 401、跨来源写入 403、资料不存在 404、数据库故障 503。

catalog.py 使用固定 Bangumi 主机、公开只读接口、超时与有限大小的上游响应缓存。搜索/日历响应缓存约 10 分钟；详情快照约 24 小时，错误回退明确提示。临时视频 URL 不进入资料缓存或数据库。测试使用临时数据库和模拟上游；当前 TestClient 的弃用提示保持原状，不为本轮改动替换测试依赖。

## 版本与学习入口

当前后端版本 0.5.0，运行依赖不变，仍按现有双终端方式启动。指南 06 保留旧单源阶段记录，指南 07 F 描述当前聚合接口；不得将实现已完成视为本人已阅读或掌握。
