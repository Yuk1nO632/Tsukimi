import "./globals.css";
import Link from "next/link";

import { AccountProvider } from "../components/account-provider";
import SiteHeader from "../components/site-header";
import Brand from "../components/brand";
import {
  CollectionFeedback,
  CollectionProvider,
  CollectionStatus,
} from "../components/collection-provider";
export const metadata = {
  title: { default: "Tsukimi · 番剧与追番", template: "%s · Tsukimi" },
  description: "搜索番剧资料，查看放送安排，管理追番片单。",
};
export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){var t="system";try{t=localStorage.getItem("tsukimi-theme")||"system"}catch(e){}document.documentElement.dataset.theme=t==="dark"||t!=="light"&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"})()` }} />
      </head>
      <body>
        <AccountProvider><CollectionProvider>
          <SiteHeader />
          <CollectionStatus />
          <main>{children}</main>
          <CollectionFeedback />
          <footer className="site-footer content-shell">
            <Brand footer />
            <div>
              <a href="https://bgm.tv" target="_blank" rel="noreferrer">
                番剧资料与放送安排：Bangumi ↗
              </a>
              <span>播放来源 AniCh / 稀饭动漫</span>
            </div>
            <nav aria-label="页脚导航">
              <Link href="/browse">番剧索引</Link>
              <Link href="/calendar">放送日历</Link>
              <Link href="/collection">我的追番</Link>
            </nav>
          </footer>
        </CollectionProvider></AccountProvider>
      </body>
    </html>
  );
}
