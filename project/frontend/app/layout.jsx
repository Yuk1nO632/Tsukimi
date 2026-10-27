import "./globals.css";
import Link from "next/link";
import { Suspense } from "react";
import SiteHeader from "../components/site-header";
import {
  CollectionFeedback,
  CollectionProvider,
  CollectionStatus,
} from "../components/collection-provider";
export const metadata = {
  title: { default: "Tsukimi · 番剧与追番", template: "%s · Tsukimi" },
  description: "搜索番剧资料，查看放送安排，管理追番片单。",
  icons: { icon: "data:," },
};
export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth">
      <body>
        <CollectionProvider>
          <Suspense fallback={<div className="site-header" />}>
            <SiteHeader />
          </Suspense>
          <CollectionStatus />
          <main>{children}</main>
          <CollectionFeedback />
          <footer className="site-footer content-shell">
            <Link className="footer-brand" href="/">
              ☾ Tsukimi
            </Link>
            <div>
              <a href="https://bgm.tv" target="_blank" rel="noreferrer">
                番剧资料与放送安排：Bangumi ↗
              </a>
              <span>播放来源：稀饭动漫</span>
            </div>
            <nav aria-label="页脚导航">
              <Link href="/browse">番剧索引</Link>
              <Link href="/calendar">放送日历</Link>
              <Link href="/collection">我的追番</Link>
            </nav>
          </footer>
        </CollectionProvider>
      </body>
    </html>
  );
}
