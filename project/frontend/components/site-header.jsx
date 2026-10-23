"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { useCollection } from "./collection-provider";

export default function SiteHeader() {
  const { favoriteIds } = useCollection();
  const [query, setQuery] = useState("");
  const router = useRouter();
  const pathname = usePathname();
  function search(event) {
    event.preventDefault();
    router.push(`/?q=${encodeURIComponent(query.trim())}#library`);
  }
  return (
    <header className="site-header">
      <div className="header-inner content-shell">
        <Link className="brand" href="/" aria-label="Tsukimi 首页"><span className="brand-mark" aria-hidden="true" />Tsukimi<span className="brand-caption">月见</span></Link>
        <nav className="header-navigation" aria-label="主导航"><Link href="/" className={pathname === "/" ? "nav-active" : ""}>番剧</Link><Link href="/#calendar">首播日历</Link><Link href="/?view=favorites#library">我的追番</Link></nav>
        <form className="header-search" role="search" onSubmit={search}><input aria-label="全站搜索" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="发现下一部心动番剧" /><button type="submit" aria-label="搜索番剧">⌕</button></form>
        <Link className="saved-indicator" href="/?view=favorites#library" aria-label={`我的追番，已收藏 ${favoriteIds.length} 部`}><span aria-hidden="true">♡</span><span className="saved-text">追番</span><strong>{favoriteIds.length}</strong></Link>
      </div>
    </header>
  );
}
