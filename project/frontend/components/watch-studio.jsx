"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { animeList } from "../lib/anime";
import { readPlayback } from "../lib/playback-api";
import FavoriteButton from "./favorite-button";
import MediaPlayer from "./media-player";
import SourceMatcher from "./source-matcher";

export default function WatchStudio({ anime, selectedEpisode, selectedSourceId, selectedLineId }) {
  const [wide, setWide] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [retry, setRetry] = useState(0);
  const [source, setSource] = useState({ status: "loading" });
  const router = useRouter();
  const relatedAnime = animeList.filter((item) => item.id !== anime.id).slice(0, 3);

  useEffect(() => {
    if (testMode) return;
    const controller = new AbortController();
    setSource({ status: "loading" });
    readPlayback(anime.id, selectedEpisode, selectedSourceId, selectedLineId, controller.signal)
      .then((data) => { if (!controller.signal.aborted) setSource(data); })
      .catch((error) => { if (!controller.signal.aborted) setSource({ status: "error", message: error.message || "来源暂时无法读取，请重试。" }); });
    return () => controller.abort();
  }, [anime.id, selectedEpisode, selectedSourceId, selectedLineId, retry, testMode]);

  function episodeUrl(episode, sourceId = selectedSourceId, lineId = selectedLineId) {
    const query = new URLSearchParams({ episode: String(episode) });
    if (sourceId) query.set("source", String(sourceId));
    if (lineId) query.set("line", String(lineId));
    return `/watch/${anime.id}?${query}`;
  }
  const media = testMode ? { status: "ready", url: "/media/flower.mp4", isTest: true } : source;
  const sourceLabel = testMode ? "MDN CC0 测试短片" : source.status === "ready" ? source.line_name : "稀饭动漫";

  return (
    <div className="watch-page content-shell">
      <nav className="breadcrumbs" aria-label="当前位置"><Link href="/">番剧</Link><span>›</span><Link href={`/anime/${anime.id}`}>{anime.title}</Link><span>›</span><strong>第 {String(selectedEpisode).padStart(2, "0")} 集</strong></nav>
      <div className={`watch-stage${wide ? " is-wide" : ""}`}>
        <section className="player-column" aria-label="视频播放区域">
          <MediaPlayer key={`${testMode}:${retry}:${media.url || media.status}`} media={media} poster={testMode ? undefined : anime.cover}
            label={testMode ? "MDN 播放器测试短片" : `${anime.title} 第 ${selectedEpisode} 集`}
            wide={wide} onWide={() => setWide((previous) => !previous)} onRetry={() => {if (!testMode) setSource({status:"loading"}); setRetry((previous) => previous + 1);}} />
          <div className="danmaku-bar"><span className="danmaku-label">弹幕</span><input aria-label="弹幕输入，功能尚未开放" disabled placeholder="弹幕功能暂未开放" /><button type="button" disabled>发送</button></div>
          <div className="playback-caption"><span>{testMode ? "正在试播测试短片，非当前番剧正片。" : source.status === "ready" ? `稀饭动漫 · ${source.episode_title || `第 ${selectedEpisode} 集`}` : "完成来源匹配后，即可尝试播放。"}</span><button type="button" onClick={() => setTestMode((previous) => !previous)}>{testMode ? "返回番剧来源" : "试播测试短片"}</button></div>
          <div className="watch-episode-navigation">{selectedEpisode > 1 ? <Link scroll={false} href={episodeUrl(selectedEpisode - 1)}>← 上一集</Link> : <button type="button" disabled>← 上一集</button>}<span>第 {selectedEpisode} 集 / 全 {anime.episodes} 集</span>{selectedEpisode < anime.episodes ? <Link scroll={false} href={episodeUrl(selectedEpisode + 1)}>下一集 →</Link> : <button type="button" disabled>下一集 →</button>}</div>
        </section>
        <aside className="watch-sidebar" aria-labelledby="watch-anime-title">
          <div className="watch-series-card"><Link className="watch-series-cover" href={`/anime/${anime.id}`}><Image src={anime.cover} alt="" fill sizes="82px" /></Link><div><span className="small-label">番剧 · {anime.year}</span><h1 id="watch-anime-title"><Link href={`/anime/${anime.id}`}>{anime.title}</Link></h1><p>{anime.category}</p>{anime.score > 0 && <span className="inline-rating">{anime.score.toFixed(1)} <small>Bangumi</small></span>}</div></div>
          <div className="watch-save-row"><FavoriteButton animeId={anime.id} title={anime.title} /><Link href={`/anime/${anime.id}`}>番剧详情 ›</Link></div>
          <div className="episode-selector-heading"><h2>选集</h2><span>全 {anime.episodes} 集</span></div>
          <div className="episode-selector" aria-label="选集列表">{Array.from({ length: anime.episodes }, (_, index) => <Link key={index + 1} scroll={false} href={episodeUrl(index + 1)} aria-current={selectedEpisode === index + 1 ? "page" : undefined} aria-label={`选择第 ${index + 1} 集`}>{String(index + 1).padStart(2, "0")}{selectedEpisode === index + 1 && <span aria-hidden="true">▥</span>}</Link>)}</div>
          <div className={`source-status${source.status === "ready" && !testMode ? " is-ready" : ""}`}><span className="source-dot" />{sourceLabel}<span>{testMode ? "测试模式" : source.status === "ready" ? "已取得播放地址" : source.status === "loading" ? "读取中" : "待匹配 / 重试"}</span></div>
          {source.source_title && <p className="matched-title">来源作品：{source.source_title}</p>}
          {source.lines?.length > 0 && <label className="source-line-label">播放线路<select aria-label="播放线路" disabled={testMode} value={source.line_id || ""} onChange={(event) => router.replace(episodeUrl(selectedEpisode, source.source_anime_id, Number(event.target.value)), {scroll:false})}>{source.lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>}
          {source.source_page && <a className="source-page-link" href={source.source_page} target="_blank" rel="noreferrer">在来源站查看这一集 ↗</a>}
          <SourceMatcher title={anime.title} onSelect={(id) => router.push(episodeUrl(1, id, null), {scroll:false})} />
        </aside>
      </div>
      <div className="watch-below"><section className="watch-information"><div className="watch-title-row"><div><span className="small-label">{anime.originalTitle}</span><h2>{anime.title}<span>第 {selectedEpisode} 集</span></h2></div>{anime.sourceUrl && <a href={anime.sourceUrl} target="_blank" rel="noreferrer">Bangumi 资料 ↗</a>}</div><div className="watch-tags"><span>{anime.year}</span>{anime.tags?.map((tag) => <span key={tag}>{tag}</span>)}<span>全 {anime.episodes} 集</span></div><h3>故事简介</h3><p className={`watch-synopsis${expanded ? " is-expanded" : ""}`}>{anime.synopsis || anime.description}</p><button className="text-button" type="button" onClick={() => setExpanded((previous) => !previous)} aria-expanded={expanded}>{expanded ? "收起简介 ↑" : "展开简介 ↓"}</button></section><aside className="related-panel"><h2>下一个心动故事</h2>{relatedAnime.map((item) => <Link className="related-item" key={item.id} href={`/anime/${item.id}`}><div className="related-cover"><Image src={item.cover} alt="" fill sizes="66px" /></div><div><strong>{item.title}</strong><span>{item.category}</span><small>全 {item.episodes} 集</small></div><i>›</i></Link>)}</aside></div>
    </div>
  );
}
