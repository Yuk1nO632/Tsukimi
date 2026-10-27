"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCollection } from "./collection-provider";
import HeaderSearch from "./header-search";
import { Suspense } from "react";

export default function SiteHeader() {
  const { favoriteIds, status } = useCollection();

  const pathname = usePathname();
  const links = [
    ["/", "首页"],
    ["/browse", "番剧索引"],
    ["/calendar", "放送日历"],
    ["/collection", "我的追番"],
  ];
  return (
    <header className="site-header">
      <div className="header-inner content-shell">
        <Link className="brand" href="/" aria-label="Tsukimi 首页">
          <span className="brand-mark" aria-hidden="true" />
          Tsukimi
        </Link>
        <nav className="header-navigation" aria-label="主导航">
          {links.map(([href, label]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
              className={
                pathname === href ||
                (href === "/browse" && pathname === "/search")
                  ? "nav-active"
                  : ""
              }
            >
              {label}
            </Link>
          ))}
        </nav>
        <Suspense
          fallback={
            <div
              className="header-search"
              style={{ height: 42 }}
              aria-hidden="true"
            />
          }
        >
          <HeaderSearch />
        </Suspense>
        <Link
          className="saved-indicator"
          href="/collection"
          aria-label="我的追番"
        >
          <span aria-hidden="true">♡</span>
          <span className="saved-text">追番</span>
          <strong>{status === "ready" ? favoriteIds.length : "—"}</strong>
        </Link>
      </div>
      <nav className="mobile-navigation" aria-label="手机主导航">
        {links.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            aria-current={pathname === href ? "page" : undefined}
          >
            {label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
