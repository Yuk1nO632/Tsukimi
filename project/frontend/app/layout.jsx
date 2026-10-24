import "./globals.css";
import Link from "next/link";
import SiteHeader from "../components/site-header";
import { CollectionFeedback, CollectionProvider, CollectionStatus } from "../components/collection-provider";
export const metadata = {
  title: { default: "Tsukimi · 发现下一份喜欢", template: "%s · Tsukimi" },
  description: "发现番剧、收藏喜欢，走进属于自己的放映时光。",
  icons: { icon: "data:," },
};
export default function RootLayout({ children }) {
  return <html lang="zh-CN"><body><CollectionProvider><SiteHeader /><CollectionStatus /><main>{children}</main><CollectionFeedback /><footer className="site-footer content-shell"><Link className="footer-brand" href="/">☾ Tsukimi<span>下一集，继续喜欢。</span></Link><div><a href="https://bgm.tv" target="_blank" rel="noreferrer">番剧资料来自 Bangumi ↗</a><span>视频来源尚未接入 · 本地开发版</span></div><Link href="/#library">发现更多故事 ↑</Link></footer></CollectionProvider></body></html>;
}
