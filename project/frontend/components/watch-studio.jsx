"use client";
import Image from "next/image";
import Link from "next/link";
import { useRef, useState } from "react";
import { animeList } from "../lib/anime";
import FavoriteButton from "./favorite-button";

export default function WatchStudio({ anime, selectedEpisode }) {
  const [wide, setWide] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [playerMessage, setPlayerMessage] = useState("");
  const playerRef = useRef(null);
  const relatedAnime = animeList.filter((item) => item.id !== anime.id).slice(0, 3);
  async function fullscreen() {
    try {
      if (!playerRef.current?.requestFullscreen) throw new Error("unavailable");
      await playerRef.current.requestFullscreen();
      setPlayerMessage("");
    } catch { setPlayerMessage("当前浏览器暂时无法进入全屏，可以使用宽屏模式。"); }
  }
  const episodeUrl = (episode) => `/watch/${anime.id}?episode=${episode}`;
  return (
    <div className="watch-page content-shell">
      <nav className="breadcrumbs" aria-label="当前位置"><Link href="/">番剧</Link><span>›</span><Link href={`/anime/${anime.id}`}>{anime.title}</Link><span>›</span><strong>第 {String(selectedEpisode).padStart(2, "0")} 集</strong></nav>
      <div className={`watch-stage${wide ? " is-wide" : ""}`}>
        <section className="player-column" aria-label="视频播放区域">
          <div className="player-frame" ref={playerRef}>
            <div className="player-canvas">
              <Image className="player-backdrop" src={anime.cover} alt="" fill sizes="900px" />
              <div className="player-vignette" /><span className="player-watermark">☾ TSUKIMI</span>
              <div className="player-empty"><span className="player-empty-icon" aria-hidden="true">▷</span><h2>故事已就绪，等待开场</h2><p>尚未接入视频来源，暂时无法播放</p><span className="player-episode-label">{anime.title} · 第 {String(selectedEpisode).padStart(2, "0")} 集</span><Link href={`/anime/${anime.id}`}>先了解这个故事 ↗</Link></div>
            </div>
            <div className="player-controls"><button type="button" disabled aria-label="播放，尚未接入视频来源">▶</button><span className="player-time">00:00 <i>/ --:--</i></span><div className="player-progress" aria-hidden="true"><span /></div><span className="player-source-state">等待视频源</span><button type="button" aria-pressed={wide} onClick={() => setWide((previous) => !previous)}>{wide ? "常规" : "宽屏"}</button><button type="button" onClick={fullscreen} aria-label="播放器全屏">⛶</button></div>
          </div>
          <div className="danmaku-bar"><span className="danmaku-label">弹幕</span><input aria-label="弹幕输入，功能尚未开放" disabled placeholder="弹幕功能暂未开放" /><button type="button" disabled>发送</button></div>
          {playerMessage && <p className="player-message" role="status">{playerMessage}</p>}
          <div className="watch-episode-navigation">{selectedEpisode > 1 ? <Link scroll={false} href={episodeUrl(selectedEpisode - 1)}>← 上一集</Link> : <button type="button" disabled>← 上一集</button>}<span>第 {selectedEpisode} 集 / 全 {anime.episodes} 集</span>{selectedEpisode < anime.episodes ? <Link scroll={false} href={episodeUrl(selectedEpisode + 1)}>下一集 →</Link> : <button type="button" disabled>下一集 →</button>}</div>
        </section>
        <aside className="watch-sidebar" aria-labelledby="watch-anime-title">
          <div className="watch-series-card"><Link className="watch-series-cover" href={`/anime/${anime.id}`}><Image src={anime.cover} alt="" fill sizes="82px" /></Link><div><span className="small-label">番剧 · {anime.year || "演示"}</span><h1 id="watch-anime-title"><Link href={`/anime/${anime.id}`}>{anime.title}</Link></h1><p>{anime.category}</p>{anime.score > 0 && <span className="inline-rating">{anime.score.toFixed(1)} <small>Bangumi</small></span>}</div></div>
          <div className="watch-save-row"><FavoriteButton animeId={anime.id} title={anime.title} /><Link href={`/anime/${anime.id}`}>番剧详情 ›</Link></div>
          <div className="episode-selector-heading"><h2>选集</h2><span>全 {anime.episodes} 集</span></div>
          <div className="episode-selector" aria-label="选集列表">{Array.from({ length: anime.episodes }, (_, index) => <Link key={index + 1} scroll={false} href={episodeUrl(index + 1)} aria-current={selectedEpisode === index + 1 ? "page" : undefined} aria-label={`选择第 ${index + 1} 集`}>{String(index + 1).padStart(2, "0")}{selectedEpisode === index + 1 && <span aria-hidden="true">▥</span>}</Link>)}</div>
          <div className="source-status"><span className="source-dot" />视频源待接入<span>资料与视频分开获取</span></div>
        </aside>
      </div>
      <div className="watch-below"><section className="watch-information"><div className="watch-title-row"><div><span className="small-label">{anime.originalTitle || "Tsukimi 演示条目"}</span><h2>{anime.title}<span>第 {selectedEpisode} 集</span></h2></div>{anime.sourceUrl && <a href={anime.sourceUrl} target="_blank" rel="noreferrer">Bangumi 资料 ↗</a>}</div><div className="watch-tags"><span>{anime.year || "演示"}</span>{anime.tags?.map((tag) => <span key={tag}>{tag}</span>)}<span>全 {anime.episodes} 集</span></div><h3>故事简介</h3><p className={`watch-synopsis${expanded ? " is-expanded" : ""}`}>{anime.synopsis || anime.description}</p><button className="text-button" type="button" onClick={() => setExpanded((previous) => !previous)} aria-expanded={expanded}>{expanded ? "收起简介 ↑" : "展开简介 ↓"}</button></section><aside className="related-panel"><h2>下一个心动故事</h2>{relatedAnime.map((item) => <Link className="related-item" key={item.id} href={`/anime/${item.id}`}><div className="related-cover"><Image src={item.cover} alt="" fill sizes="66px" /></div><div><strong>{item.title}</strong><span>{item.category}</span><small>全 {item.episodes} 集</small></div><i>›</i></Link>)}</aside></div>
    </div>
  );
}
