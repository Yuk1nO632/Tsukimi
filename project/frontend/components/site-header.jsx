"use client";

import Link from "next/link";
import { useCollection } from "./collection-provider";

export default function SiteHeader() {
  const { favoriteIds } = useCollection();
  return (
    <header className="site-header">
      <Link className="brand" href="/" aria-label="Tsukimi 首页">
        <span className="brand-mark" aria-hidden="true" />Tsukimi<span className="brand-caption">月见</span>
      </Link>
      <nav className="header-navigation" aria-label="主导航">
        <Link href="/">发现番剧</Link>
        <Link className="saved-indicator" href="/?view=favorites">
          <span aria-hidden="true">♡</span><span>我的追番 <strong>{favoriteIds.length}</strong></span>
        </Link>
      </nav>
    </header>
  );
}
