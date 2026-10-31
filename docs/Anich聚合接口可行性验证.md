# AniCh 聚合接口可行性验证

日期：2026-11-01。本人反馈：指南 07 尚未阅读，本轮先验证聚合播放思路，不代表已完成第 07 节复习。

## 结论与实际范围

截图中的 https://anich.sends.eu.org 在本机能匿名调用搜索、详情、剧集及视频候选接口。可以作为聚合来源的接入候选，让 Tsukimi 只实现一个 AniCh 协议适配层，把逐站解析交给其服务端维护。本轮仅完成独立只读探测，正式播放器仍使用稀饭，界面、数据库与个人片单未改变。

## 实测结果

- 服务根路径返回 404，但 /bangumi/search 正常，不能用根路径判断整个接口失效。
- 搜索“葬送的芙莉莲”得到本篇、特别篇及第二季；核对本篇为 AniCh ID 32339，共 28 集。它与 Bangumi ID 400602 不同；详情 sites 中提供 bangumi 对应关系，这有利于将来精确核对。
- /bangumi/detail/32339 返回 JSON；/bangumi/episodes/32339 返回 Protobuf，读取 28 条剧集。
- /vod/32339/1 返回 JSON 整数数组，其内容仍是 Protobuf。当前样本有 76 个候选、44 个不同的来源标识；不代表 44 个独立网站或 76 条都能播放。
- 其中 8 个候选的说明写着“第二季”，存在混季信号；即使番剧条目匹配正确，也不能盲选第一条或全部展示为已核验线路。
- 按官方控制器 urlDecode 的公开规则还原 URL。抽查 v1.adkwai.com 与 s1.kwai.net 两个地址，各只读取 1024 字节，均为 HTTP 206、video/mp4、文件头含 ftyp，Access-Control-Allow-Origin 为 *。
- 这证明可以取得实际媒体数据，但本轮未在 Tsukimi 播放器中完成浏览器解码、持续播放、拖动、HLS 或多作品验收。原生客户端能播，不等于浏览器一定能播；H.265、Referer、跨域和失效地址需逐项验证。
- 官方旧配置里的 ani.emmmm.eu.org 搜索本次返回 HTTP 500，响应 message 为 unauthorized；未尝试绕过。官方 Web 入口本次被 Cloudflare 拦截，未尝试绕过。上述成功结果来自截图指定的公开服务。

所有数量、地址状态都只是本次样本，未来可能变化；接口也没有由本项目确认的长期可用性承诺。

## 可重复探测

在 VS Code 后端终端使用现有虚拟环境，无需安装新依赖：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\backend
.\.venv\Scripts\python.exe probe_anich.py --query "葬送的芙莉莲"
.\.venv\Scripts\python.exe probe_anich.py --query "葬送的芙莉莲" --id 32339 --episode 1 --probe-media
```

第一条只搜索；核对作品后第二条读取详情、剧集和视频候选，并检查最多两个不同主机的媒体前 1KB。脚本只输出主机和资料，不打印完整临时播放 URL，不保存账号或个人数据，不下载整集。服务返回格式变化会报错，不把失败当作可播放。

probe_anich.py 中的通用 Protobuf wire 读取器仅供这次探测；正式接入优先使用可维护的协议定义与库。字段 1–4 对照公开描述符，字段 5/6 是本次响应观察到的来源标识与说明，不视为已发布的稳定协议。

## 正式接入的推进顺序

1. 保持 Bangumi 资料、追番 Cookie/SQLite 不变；后端增加 AniCh 适配层，统一成当前播放器读取的字段。
2. 搜索并核对 AniCh 条目，优先检查详情 sites 的 Bangumi ID；本篇、续作与特别篇不能混用编号。
3. 逐集取得候选，去重、保留原始标识，核对混季信号并测试 Web 可播性；不把候选数量等同于可用线路数量。
4. 先对两部番剧验证第一/二集、换线、拖动与失败恢复；再考虑默认启用，稀饭保留备用。禁止自动保存签名视频 URL。
5. 复习仍先看指南 07 的搜索 → 详情 → 追番状态闭环；聚合接口只补充“同一个后端适配多条线路”的概念，不要求现在掌握 Protobuf。

## 核验依据

- [AniCh 官方仓库说明](https://github.com/Sle2p/AniCh#说明)：公开源码注明对应 1.0.0，不能当作现客户端的完整协议保证。
- [官方搜索调用](https://github.com/Sle2p/AniCh/blob/main/lib/src/apis/search.dart)
- [官方剧集与播放调用](https://github.com/Sle2p/AniCh/blob/main/lib/src/apis/bangumi.dart)
- [官方 Protobuf 描述符](https://github.com/Sle2p/AniCh/blob/main/lib/protobuf/bangumi.pbjson.dart)
- [官方播放控制器及 URL 解码](https://github.com/Sle2p/AniCh/blob/main/lib/src/pages/bangumi_vod/controller.dart)
- [官方旧接口配置](https://github.com/Sle2p/AniCh/blob/main/api.json)