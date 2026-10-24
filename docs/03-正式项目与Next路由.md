# 正式项目第一阶段：Next.js 首页与详情

> 历史阶段说明：本节对应 b062184 的基础前端。2026-10-24 起首页已改版并接入真实资料，新增播放页；旧虚构演示条目已移除。收藏也已接上后端与 SQLite。当前功能以 README、04-番剧频道与真实资料.md 和 05-收藏接口与数据库.md 为准。


从这个阶段开始，正式功能持续写入 `project/`，复习穿插在实际开发中。前两个实验留作对照。

## 本轮成果

- 首页显示三部虚构番剧，支持名称或分类搜索、收藏筛选。
- 点击封面或标题进入 `/anime/forest` 等独立详情地址。
- 详情展示简介、集数与尚未接入视频的剧集占位。
- 首页、详情和顶部导航共享收藏 state，站内跳转保留状态。
- 直接输入或刷新详情地址仍可打开；不存在的条目进入 404 页面。

## VS Code 启动

```powershell
cd C:\Users\lx\Desktop\Tsukimi\project\frontend
npm.cmd run dev
```

打开 http://127.0.0.1:3000。依赖已安装，新环境先 `npm.cmd ci`。生产构建用 `npm.cmd run build`。端口被占用时，检查是否已有终端运行本项目；需要换端口可运行 `npm.cmd run dev -- --port 3001`，以终端实际输出为准。

## 这次 Next.js 增加了什么

上一版由 Vite 帮助运行 React，这一版由 Next.js 提供开发、构建和路由能力，React 组件、props 和 state 继续使用。

- `app/layout.jsx` 是公共外壳：首页与详情共用顶部导航、收藏 Provider 和页脚。
- `app/page.jsx` 对应首页 `/`。
- `app/anime/[id]/page.jsx` 对应 `/anime/forest` 等详情地址，`id` 来自 URL。
- `next/link` 提供站内导航，减少整页重新启动，让公共 layout 中的状态能够继续保留。
- 使用 state 和点击事件的组件标记为 `"use client"`。页面本身可在服务端生成；目前不必深入服务端组件实现。

`[id]` 是实际文件夹名字，方括号表示动态路由。`params` 和 `searchParams` 按当前 Next.js 的异步接口读取。

## 为什么收藏能跨页面保持

`CollectionProvider` 放在根 layout 中，通过 Context 让首页、详情按钮和顶部计数读取同一份收藏 state。Context 可理解为把共享数据提供给一组后代组件的机制；它没有增加数据库。

站内 Link 导航时公共 Provider 保留，所以收藏还在。完整刷新会重新启动应用，所以收藏归零。新开浏览器标签页也会得到独立的初始状态。

## 亲自验收

1. 首页搜索“月光”，确认只剩匹配条目；清除后恢复三部。
2. 搜索不存在的关键词，观察空状态，再返回全部。
3. 收藏第一部，点击它的标题进入详情，确认仍显示“已收藏”。
4. 在详情取消收藏，点击“返回发现”，确认顶部计数与首页一起变化。
5. 在详情收藏，点击顶部“我的追番”，确认只显示收藏内容。
6. 直接输入 `http://127.0.0.1:3000/anime/forest`，刷新后详情仍可显示；收藏会重新归零。
7. 输入不存在的 `/anime/missing`，确认出现未找到页面，可返回发现。

剧集列表现在只展示结构，没有视频来源和播放按钮。后续先接 FastAPI 与 SQLite，让收藏保存，再验证一个真实播放来源。

## Git 如何配合这一阶段

在 VS Code 的“源代码管理”中查看文件变化，或到工作区根目录运行 `git status`、`git diff`。一个阶段完成并验证后，提交有意义的记录。Git 仓库位于工作区根，不要在 frontend 中重复初始化。

## 官方参考

- Next.js 安装：https://nextjs.org/docs/app/getting-started/installation
- 动态路由：https://nextjs.org/docs/app/api-reference/file-conventions/dynamic-routes
- 服务端与客户端组件：https://nextjs.org/docs/app/getting-started/server-and-client-components
