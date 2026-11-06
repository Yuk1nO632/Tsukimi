"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useCollection } from "./collection-provider";
import { useAccount } from "./account-provider";
import HeaderSearch from "./header-search";
import Brand from "./brand";
import { Suspense } from "react";

export default function SiteHeader() {
  const { favoriteIds, status } = useCollection();

  const account = useAccount();
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
        <Brand />
        <nav className="header-navigation" aria-label="主导航">
          {links.map(([href, label]) => (
            <Link
              key={href}
              prefetch={true}
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
        <Link href="/account" className="header-account" aria-label={account.user ? "我的账号" : "登录或注册"}>
          <span aria-hidden="true">{account.user?.nickname.slice(0, 1) || "☾"}</span>
          <span>{account.user?.nickname || "登录"}</span>
        </Link>
      </div>
      <nav className="mobile-navigation" aria-label="手机主导航">
        {links.map(([href, label]) => (
          <Link
            key={href}
            prefetch={true}
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
