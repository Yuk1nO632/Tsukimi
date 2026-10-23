"use client";

import { useRef, useState } from "react";
import { animeList } from "../lib/anime";
import { useCollection } from "./collection-provider";
import AnimeCard from "./anime-card";

export default function HomeLibrary({ initialView }) {
  const { favoriteIds } = useCollection();
  const [view, setView] = useState(initialView);
  const [query, setQuery] = useState("");
  const favoritesFilterRef = useRef(null);
  const allFilterRef = useRef(null);
  const searchTerm = query.trim().toLocaleLowerCase();
  const visibleAnime = animeList.filter((anime) => {
    const matchesView = view === "all" || favoriteIds.includes(anime.id);
    const matchesQuery = `${anime.title} ${anime.category}`.toLocaleLowerCase().includes(searchTerm);
    return matchesView && matchesQuery;
  });

  function showAll() {
    setQuery("");
    setView("all");
    allFilterRef.current?.focus({ preventScroll: true });
  }

  return (
    <section className="library" aria-labelledby="library-title">
      <div className="section-heading">
        <div><span className="eyebrow">YOUR LITTLE COLLECTION</span><h2 id="library-title">发现喜欢的故事 <span className="library-total">{String(animeList.length).padStart(2, "0")}</span></h2></div>
        <div className="filters" role="group" aria-label="番剧筛选">
          <button ref={allFilterRef} className={`filter-button${view === "all" ? " is-active" : ""}`} type="button" aria-pressed={view === "all"} onClick={() => setView("all")}>全部</button>
          <button ref={favoritesFilterRef} className={`filter-button${view === "favorites" ? " is-active" : ""}`} type="button" aria-pressed={view === "favorites"} onClick={() => setView("favorites")}>已收藏 <span>{favoriteIds.length}</span></button>
        </div>
      </div>
      <div className="search-row">
        <label className="search-label" htmlFor="anime-search">搜索番剧</label>
        <div className="search-input-wrap">
          <input id="anime-search" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索名称或分类，例如：月光、治愈" autoComplete="off" />
          {query && <button type="button" onClick={() => setQuery("")} aria-label="清除搜索">清除</button>}
        </div>
        <span className="search-result-count" role="status" aria-live="polite">{visibleAnime.length} 部故事</span>
      </div>
      <div className="anime-grid" hidden={visibleAnime.length === 0}>
        {visibleAnime.map((anime) => (
          <AnimeCard key={anime.id} anime={anime} number={animeList.findIndex((item) => item.id === anime.id) + 1} onBeforeToggle={(wasFavorite) => {
            if (wasFavorite && view === "favorites") favoritesFilterRef.current?.focus({ preventScroll: true });
          }} />
        ))}
      </div>
      {visibleAnime.length === 0 && (
        <div className="empty-state">
          <span aria-hidden="true">☾</span>
          <h3>{searchTerm ? "还没找到这个故事" : "这里还没有收藏"}</h3>
          <p>{searchTerm ? "换个关键词试试，或浏览全部演示条目。" : "打开喜欢的故事，为它留一个位置。"}</p>
          <button type="button" onClick={showAll}>浏览全部</button>
        </div>
      )}
      <p className="demo-caption">当前为 3 部虚构演示番剧。真实资料与播放来源会在后续阶段接入。</p>
    </section>
  );
}
