# 实验 02：React 组件、props 与 state

预计 45–75 分钟。继续使用相同的追番卡片和收藏操作，重点比较代码的组织方式。本轮没有数据库、登录或真实视频。

## 先带上上一课的结论

收藏曾保存在页面 JavaScript 内存中。刷新会重新运行页面代码，集合重新变空。Python 静态文件服务器负责把文件提供给浏览器，并不负责保存收藏。

React 的 state 也不是磁盘存储。它能让组件在多次渲染之间记住数据、通过更新函数触发界面更新，但刷新或组件被卸载仍可能重置状态。

## 1. 在 VS Code 中启动

继续打开整个 `C:\Users\lx\Desktop\Tsukimi` 文件夹，在新终端中运行：

```powershell
cd C:\Users\lx\Desktop\Tsukimi\experiments\02-react-state
npm.cmd run dev
```

当前环境已安装好依赖。换电脑或依赖目录不存在时，先运行一次 `npm.cmd install`；有锁文件时可以用 `npm.cmd ci` 恢复锁定版本。

在浏览器打开 <http://127.0.0.1:5174>。结束时在对应终端按 `Ctrl+C`。

- 使用 `npm.cmd` 是为了避免 Windows PowerShell 对 `npm.ps1` 的执行策略限制；无需修改系统策略。
- 原来的 Python 服务可以继续占用 5173，两个实验可同时对照。
- 5174 被占用时，先检查是否已启动了这一实验；需要换端口可运行 `npm.cmd run dev -- --port 5175`，访问终端实际打印的地址。
- 这次不能双击 HTML 或用 Python 直接提供源文件来运行；JSX 和 npm 模块由 Vite 转换后交给浏览器。

## 2. 看懂运行路径

```text
终端运行 npm.cmd run dev
  → npm 执行 package.json 中的 dev 命令
  → Node.js 运行 Vite 开发服务器
  → 浏览器请求页面及转换后的模块
  → React 在浏览器中运行，显示 App
```

Node.js / Vite 在本轮提供开发服务；它们还不是业务后端。点击收藏后，收藏 state 仍由浏览器中的 React 管理。Vite 的热更新连接也不代表收藏已经上传保存。

## 3. 只看这几个文件

| 文件 | 作用 | 先看哪里 |
| --- | --- | --- |
| `package.json` | 依赖和运行命令 | `scripts.dev`、`react`、`vite` |
| `index.html` | 页面入口和挂载位置 | `<div id="root">` |
| `src/main.jsx` | 启动 React 并加载样式 | `createRoot(...).render(<App />)` |
| `src/App.jsx` | 页面整体、共享状态和事件处理 | `useState`、`toggleFavorite`、`<AnimeCard ... />` |
| `src/components/AnimeCard.jsx` | 可重复使用的番剧卡片 | 接收的四个 props |
| `src/data.js` | 三部虚构番剧的数据 | 不同条目使用不同 id |

`src/styles.css` 复制了上一实验的样式，外观沿用，不需要重读全部 CSS。`useRef` 只辅助键盘焦点，本课不要求掌握。`node_modules`、构建结果和锁文件也不用逐行阅读；锁文件用于固定安装版本，不要随意修改。

## 4. 组件：一份结构，生成多张卡片

以前用 template 克隆卡片，再用 JavaScript 找到标题、按钮并逐项填写。

现在 `AnimeCard` 是一个返回 JSX 的函数组件，App 根据数据列表多次使用它。卡片结构只有一份，但可以展示三部不同的番剧。

观察：在 `AnimeCard.jsx` 中把按钮文字“收藏”临时改为“加入追番”。保存后所有未收藏卡片都会一起变化。验证后恢复原文字。

这里像 HTML 的写法是 JSX，例如 `className` 对应 HTML 的 `class`；大括号里可以放 JavaScript 表达式。

## 5. props：父组件把信息传给子组件

找到 App 中：

```jsx
<AnimeCard
  key={anime.id}
  anime={anime}
  number={animeList.findIndex((item) => item.id === anime.id) + 1}
  isFavorite={favoriteIds.includes(anime.id)}
  onToggle={toggleFavorite}
/>
```

这段结构与 App 中的实际代码一致；先理解传入了哪些信息，不必记住序号计算的写法。

- `anime`：这张卡片显示哪部番剧。
- `number`：海报右下角的序号。
- `isFavorite`：是否显示“已收藏”。
- `onToggle`：点击时通知 App 处理收藏。

`key` 用于 React 识别列表条目，不是 AnimeCard 接收到的普通 prop。

卡片不直接修改传入的资料或自己的收藏副本。它调用 App 给它的函数，App 更新收藏状态，再把新的结果传回来。顶部计数与卡片共用同一份状态。

## 6. state：记住变化，并让界面更新

在 `App.jsx` 找到：

```jsx
const [favoriteIds, setFavoriteIds] = useState([]);
```

- `favoriteIds`：当前这一轮渲染拿到的收藏 id 数组。
- `setFavoriteIds`：请求 React 更新状态的函数。
- `[]`：首次建立这个组件状态时的初始值。

点击收藏后的路径是：

```text
卡片按钮 onClick
  → onToggle(anime.id)
  → App 的 toggleFavorite
  → setFavoriteIds 更新收藏
  → React 再次渲染相关组件
  → 计数、按钮和筛选结果随新数据变化
```

注意区分：重新渲染不会把现有 state 自动重置为 `[]`；完整刷新会重新启动应用，才会重新使用初始值。

实验中更新数组时创建新数组，没有直接使用 `push` 修改原数组，也没有手动调用上一实验的 `render()` 或修改卡片的 `textContent`。`setFavoriteIds` 中的函数接收待更新的前一份状态，计算下一份状态。

## 7. 亲自验证四件事

1. 收藏两部番剧：顶部计数和筛选计数一起变成 2。
2. 切换“全部 / 已收藏”：收藏保持，切换筛选不会清空它。
3. 在“已收藏”中逐个取消：列表减少，最后出现空状态。键盘焦点会回到筛选按钮。
4. 收藏一部后完整刷新浏览器：计数重新归零，React 没有替你做持久化。

改代码后的热更新有时会保留 state，有时会重置，不能用它判断刷新是否持久保存。第 4 步请使用浏览器的完整刷新按钮。

## 8. 做一次数据驱动的小修改

把 `src/data.js` 中第一部的 `episodes` 改成 24，保存后观察对应卡片是否变化，再恢复。数据描述“显示什么”，组件描述“怎么显示”。

## 完成后记录

在学习记录中回答：

1. 为什么只改一份 AnimeCard，多个卡片都会变化？
2. props 与 state 在这个实验中分别是什么？
3. 为什么收藏状态放在 App，顶部计数也能同步变化？
4. 重新渲染与刷新浏览器，对 state 有什么不同？

下一实验再进入 Next.js 路由和详情页。本轮先把组件、传数据、更新状态这三件事弄清楚。

## 官方参考

- React 组件之间传递 props：https://react.dev/learn/passing-props-to-a-component
- React 组件的记忆 state：https://react.dev/learn/state-a-components-memory
- Vite 入门：https://vite.dev/guide/
