import "./globals.css";
import Link from "next/link";
import SiteHeader from "../components/site-header";
import { CollectionFeedback, CollectionProvider } from "../components/collection-provider";

export const metadata = {
  title: { default: "Tsukimi · 月见", template: "%s · Tsukimi" },
  description: "收藏喜欢的故事，期待下一次相见。Tsukimi 个人追番 Web 项目。",
  icons: { icon: "data:," },
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>
        <CollectionProvider>
          <div className="page-shell">
            <SiteHeader />
            <main>{children}</main>
            <CollectionFeedback />
            <footer><span>Tsukimi <span className="footer-dot">·</span> 下一集，继续喜欢。</span><Link href="/">回到发现</Link></footer>
          </div>
        </CollectionProvider>
      </body>
    </html>
  );
}
