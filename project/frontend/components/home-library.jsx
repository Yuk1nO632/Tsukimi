"use client";
import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";
import { animeList, catalogMeta } from "../lib/anime";
import { useCollection } from "./collection-provider";
import AnimeCard from "./anime-card";

const genres = ["全部", "奇幻", "治愈", "日常", "音乐", "悬疑"];
const weekdays = ["全部", "周一", "周二", "周三", "周四", "周五", "周六", "周日"];

export default function HomeLibrary({ initialView, initialQuery = "" }) {
  const { favoriteIds } = useCollection();
  const [view, setView] = useState(initialView);
  const [query, setQuery] = useState(initialQuery);
  const [genre, setGenre] = useState("全部");
  const [weekday, setWeekday] = useState(0);
  const favoritesRef = useRef(null);
  const allRef = useRef(null);
  const searchTerm = query.trim().toLocaleLowerCase();
  const visibleAnime = animeList.filter((anime) => (view === "all" || favoriteIds.includes(anime.id)) && (genre === "全部" || anime.tags.includes(genre)) && `${anime.title} ${anime.originalTitle} ${anime.category}`.toLocaleLowerCase().includes(searchTerm));
  const scheduledAnime = animeList.filter((anime) => weekday === 0 || anime.releaseWeekday === weekday);
  const savedAnime = animeList.filter((anime) => favoriteIds.includes(anime.id));
  function showAll() { setQuery(""); setGenre("全部"); setView("all"); allRef.current?.focus({ preventScroll: true }); }
  return (
    <div className="content-shell homepage-content">
      <div className="discovery-shortcuts" aria-label="快捷入口"><Link className="shortcut shortcut-pink" href="/#library"><span className="shortcut-icon" aria-hidden="true">▧</span><div><strong>番剧索引 <i>›</i></strong><small>从兴趣出发，找到下一部</small></div></Link><Link className="shortcut shortcut-blue" href="/#calendar"><span className="shortcut-icon" aria-hidden="true">▦</span><div><strong>首播日历 <i>›</i></strong><small>按原始首播日浏览片单</small></div></Link><Link className="shortcut shortcut-purple" href="/?view=favorites#library"><span className="shortcut-icon" aria-hidden="true">♡</span><div><strong>我的追番 <i>›</i></strong><small>喜欢的故事，都在这里</small></div><b>{favoriteIds.length}</b></Link></div>
      <section className="library" id="library" aria-labelledby="library-title">
        <div className="section-heading"><div className="section-title"><span className="section-icon pink" aria-hidden="true">✦</span><h2 id="library-title">{view === "favorites" ? "我的追番" : "为你发现"}</h2><span className="section-subtitle">下一份喜欢，就在这里</span></div><div className="filters" role="group" aria-label="番剧筛选"><button ref={allRef} className={`filter-button${view === "all" ? " is-active" : ""}`} type="button" aria-pressed={view === "all"} onClick={() => setView("all")}>全部番剧</button><button ref={favoritesRef} className={`filter-button${view === "favorites" ? " is-active" : ""}`} type="button" aria-pressed={view === "favorites"} onClick={() => setView("favorites")}>已收藏 {favoriteIds.length}</button></div></div>
        <div className="catalog-toolbar"><div className="genre-tabs" role="group" aria-label="番剧分类">{genres.map((item) => <button key={item} className={genre === item ? "is-active" : ""} type="button" aria-pressed={genre === item} onClick={() => setGenre(item)}>{item}</button>)}</div><div className="search-input-wrap"><input id="anime-search" aria-label="搜索番剧" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索片名、分类" autoComplete="off" />{query && <button type="button" onClick={() => setQuery("")} aria-label="清除搜索">×</button>}</div></div>
        <div className="result-summary" role="status" aria-live="polite">共 {visibleAnime.length} 部番剧<span>资料来源：Bangumi · {catalogMeta.syncedAt.slice(0, 10)}</span></div>
        <div className="anime-grid" hidden={visibleAnime.length === 0}>{visibleAnime.map((anime) => <AnimeCard key={anime.id} anime={anime} onBeforeToggle={(wasFavorite) => { if (wasFavorite && view === "favorites") favoritesRef.current?.focus({ preventScroll: true }); }} />)}</div>
        {visibleAnime.length === 0 && <div className="empty-state"><span aria-hidden="true">☾</span><h3>{searchTerm || genre !== "全部" ? "还没找到这个故事" : "这里还没有收藏"}</h3><p>换个关键词，或为喜欢的番剧点一下收藏。</p><button type="button" onClick={showAll}>浏览全部</button></div>}
      </section>
      <div className="homepage-lower"><section className="calendar-panel" id="calendar" aria-labelledby="calendar-title"><div className="section-heading"><div className="section-title"><span className="section-icon blue" aria-hidden="true">▦</span><h2 id="calendar-title">首播日历</h2></div><span className="subtle-note">原始首播日期，非当前更新排期</span></div><div className="weekday-tabs" role="group" aria-label="首播星期">{weekdays.map((label, index) => <button key={label} type="button" aria-pressed={weekday === index} className={weekday === index ? "is-active" : ""} onClick={() => setWeekday(index)}>{label}</button>)}</div><div className="calendar-list">{scheduledAnime.length === 0 ? <p className="small-empty">这一天暂时没有收录条目，试试其他日期。</p> : scheduledAnime.map((anime) => <Link className="calendar-item" href={`/anime/${anime.id}`} key={anime.id}><div className="calendar-cover"><Image src={anime.cover} alt="" fill sizes="65px" /></div><div><strong>{anime.title}</strong><span>{anime.releaseDate} 首播</span><small>{anime.category}</small></div><i>›</i></Link>)}</div></section><aside className="personal-panel" aria-labelledby="personal-title"><div className="section-title"><span className="section-icon purple" aria-hidden="true">♡</span><h2 id="personal-title">留给喜欢的位置</h2></div><p className="personal-copy">不赶进度，只追喜欢。</p>{savedAnime.length > 0 ? <div className="personal-list">{savedAnime.slice(0, 3).map((anime) => <Link key={anime.id} href={`/anime/${anime.id}`}><div className="personal-cover"><Image src={anime.cover} alt="" fill sizes="44px" /></div><div><strong>{anime.title}</strong><span>已加入追番</span></div><i>›</i></Link>)}</div> : <div className="personal-empty"><span aria-hidden="true">☾</span><strong>你的片单，等一个开场</strong><p>收藏一部心动番剧，<br />让下一次相见更容易。</p><a href="#library">去发现喜欢的番剧 ↗</a></div>}<div className="personal-tip"><span>月见手记</span><p>总有一些故事，值得慢慢看。</p></div></aside></div>
    </div>
  );
}
