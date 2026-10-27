"use client";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useCollection } from "./collection-provider";
import PlayerIcon from "./player-icon";

export default function SiteHeader() {
  const { favoriteIds, status } = useCollection();
  const params = useSearchParams();
  const queryInUrl = params.get("q") || "";
  const [query, setQuery] = useState(queryInUrl);
  const router = useRouter();
  const pathname = usePathname();
  useEffect(() => setQuery(queryInUrl), [queryInUrl]);
  function search(event) {
    event.preventDefault();
    router.push(
      query.trim()
        ? `/search?q=${encodeURIComponent(query.trim())}`
        : "/browse",
    );
  }
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
        <form className="header-search" role="search" onSubmit={search}>
          <input
            name="q"
            aria-label="搜索番剧资料"
            maxLength={100}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索番名、原名或别名"
          />
          <button type="submit" aria-label="搜索番剧">
            <PlayerIcon name="search" size={19} />
          </button>
        </form>
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
