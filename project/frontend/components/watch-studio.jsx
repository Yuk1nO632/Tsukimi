"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { animeList } from "../lib/anime";
import { readPlayback } from "../lib/playback-api";
import FavoriteButton from "./favorite-button";
import MediaPlayer from "./media-player";
import SourceMatcher from "./source-matcher";
import PlayerIcon from "./player-icon";

export default function WatchStudio({ anime, selectedEpisode, selectedSourceId, selectedLineId }) {
  const [wide, setWide] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [retry, setRetry] = useState(0);
  const [copyMessage, setCopyMessage] = useState("");
  const [source, setSource] = useState({ status: "loading" });
  const helpRef = useRef(null);
  const sourcePanelRef = useRef(null);
  const sourceInputRef = useRef(null);
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
  useEffect(() => {
    if (!copyMessage) return;
    const timer = window.setTimeout(() => setCopyMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [copyMessage]);

  useEffect(() => {
    function closeHelp(event) {
      const help = helpRef.current;
      if (help?.open && (event.key === "Escape" || (event.type === "pointerdown" && !help.contains(event.target)))) help.open = false;
    }
    document.addEventListener("pointerdown", closeHelp);
    document.addEventListener("keydown", closeHelp);
    return () => { document.removeEventListener("pointerdown", closeHelp); document.removeEventListener("keydown", closeHelp); };
  }, []);
  function episodeUrl(episode, sourceId = selectedSourceId, lineId = selectedLineId) {
    const query = new URLSearchParams({ episode: String(episode) });
    if (sourceId) query.set("source", String(sourceId));
    if (lineId) query.set("line", String(lineId));
    return `/watch/${anime.id}?${query}`;
  }
  function findSource() {
    sourcePanelRef.current?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "center" });
    sourceInputRef.current?.focus({ preventScroll: true });
    sourceInputRef.current?.select();
  }
  function reloadSource() {
    if (!testMode) setSource({ status: "loading" });
    setRetry((previous) => previous + 1);
  }
  async function copyLink() {
    try { await navigator.clipboard.writeText(window.location.href); setCopyMessage("播放页链接已复制"); }
    catch { setCopyMessage("复制未成功，请复制浏览器地址栏中的网址。"); }
  }
  const media = testMode ? { status: "ready", url: "/media/flower.mp4", isTest: true } : source;
  const ready = source.status === "ready";
  const sourceLabel = source.status === "loading" ? "连接中" : ready ? "已匹配" : "需要选择来源";
  const nextHref = selectedEpisode < anime.episodes ? episodeUrl(selectedEpisode + 1) : null;

  return <div className="watch-page content-shell">
    <nav className="breadcrumbs" aria-label="当前位置"><Link href="/">番剧频道</Link><span>›</span><Link href={`/anime/${anime.id}`}>{anime.title}</Link><span>›</span><strong>正在观看</strong></nav>
    <div className={`watch-stage${wide ? " is-wide" : ""}`}>
      <section className="player-column" aria-label="视频播放区域">
        <MediaPlayer key={`${testMode}:${retry}:${media.url || media.status}`} media={media} poster={testMode ? undefined : anime.cover}
          label={testMode ? "MDN 播放器测试短片" : `${anime.title} · 第 ${selectedEpisode} 集`}
          wide={wide} onWide={() => setWide((previous) => !previous)} onRetry={reloadSource} onFindSource={findSource} nextHref={nextHref} />
        <div className="watch-now"><div><span className="watch-now-kicker">{testMode ? "播放器测试" : "正在观看"}</span><h2>{anime.title}<span>第 {String(selectedEpisode).padStart(2, "0")} 集</span></h2></div><button type="button" className="watch-share" onClick={copyLink}>复制链接 ↗</button></div>
        <div className="watch-episode-navigation">{selectedEpisode > 1 ? <Link scroll={false} href={episodeUrl(selectedEpisode - 1)}>← 上一集</Link> : <button type="button" disabled>← 上一集</button>}<span>第 {selectedEpisode} 集 / 全 {anime.episodes} 集</span>{nextHref ? <Link className="next-episode-link" scroll={false} href={nextHref}>下一集 <PlayerIcon name="next" size={15} /></Link> : <button type="button" disabled>已是最后一集</button>}</div>
        <div className="watch-assist"><span className="playback-origin">{testMode ? "测试短片 · 非番剧正片" : ready ? `稀饭动漫 · ${source.episode_title || `第 ${selectedEpisode} 集`}` : "搜索并选择来源后，即可开始观看"}</span><details className="playback-help" ref={helpRef}><summary>播放帮助</summary><div><p>点击画面播放 / 暂停，双击全屏。选中播放器后：空格暂停，← → 跳转 5 秒，↑ ↓ 调节音量，M 静音，F 全屏。</p><p>播放时控制栏会自动收起，移动鼠标或触碰画面即可唤回。</p><button type="button" onClick={() => { if (helpRef.current) helpRef.current.open = false; setTestMode((previous) => !previous); }}>{testMode ? "返回番剧来源" : "试播测试短片"}</button></div></details></div>
        {testMode && <div className="test-mode-banner">当前是约 5 秒的播放器测试短片。<button type="button" onClick={() => setTestMode(false)}>返回番剧正片 →</button></div>}
        {copyMessage && <p className="watch-copy-feedback" role="status">{copyMessage}</p>}
      </section>
      <aside className="watch-sidebar" aria-labelledby="watch-anime-title">
        <div className="watch-series-card"><Link className="watch-series-cover" href={`/anime/${anime.id}`}><Image src={anime.cover} alt="" fill sizes="76px" /></Link><div><span className="small-label">番剧 · {anime.year}</span><h1 id="watch-anime-title"><Link href={`/anime/${anime.id}`}>{anime.title}</Link></h1><p>{anime.category}</p>{anime.score > 0 && <span className="inline-rating">{anime.score.toFixed(1)} <small>Bangumi</small></span>}</div></div>
        <div className="watch-save-row"><FavoriteButton animeId={anime.id} title={anime.title} /><Link href={`/anime/${anime.id}`}>作品详情 →</Link></div>
        <section className={`watch-source-panel${!ready ? " needs-source" : ""}`} ref={sourcePanelRef} aria-labelledby="source-panel-title">
          <div className="source-panel-heading"><h2 id="source-panel-title">播放来源 <span>稀饭动漫</span></h2><span className={`source-badge${ready ? " is-ready" : ""}`}><i />{sourceLabel}</span></div>
          <SourceMatcher title={anime.title} inputRef={sourceInputRef} selectedId={source.source_anime_id} onSelect={(id) => { setTestMode(false); router.push(episodeUrl(1, id, null), { scroll: false }); }} />
          {ready && <div className="source-current"><span>当前作品</span><strong>{source.source_title}</strong></div>}
          {source.lines?.length > 0 && <label className="source-line-label">播放线路<select aria-label="播放线路" disabled={testMode} value={source.line_id || ""} onChange={(event) => router.replace(episodeUrl(selectedEpisode, source.source_anime_id, Number(event.target.value)), { scroll: false })}>{source.lines.map((line) => <option key={line.id} value={line.id}>{line.name}</option>)}</select></label>}
          <div className="source-panel-actions"><button type="button" disabled={source.status === "loading" || testMode} onClick={reloadSource}><PlayerIcon name="refresh" size={13} />重新连接</button>{source.source_page && <a href={source.source_page} target="_blank" rel="noreferrer">前往来源站 ↗</a>}</div>
        </section>
        <section className="watch-episodes-panel" aria-labelledby="episodes-title"><div className="episode-selector-heading"><h2 id="episodes-title">选集</h2><span>全 {anime.episodes} 集</span></div>
          <div className="episode-selector" aria-label="选集列表">{Array.from({ length: anime.episodes }, (_, index) => <Link key={index + 1} scroll={false} href={episodeUrl(index + 1)} aria-current={selectedEpisode === index + 1 ? "page" : undefined} aria-label={`选择第 ${index + 1} 集`}>{String(index + 1).padStart(2, "0")}{selectedEpisode === index + 1 && <span className="episode-playing" aria-hidden="true"><i /><i /><i /></span>}</Link>)}</div>
        </section>
      </aside>
    </div>
    <div className="watch-below"><section className="watch-information"><div className="watch-title-row"><div><span className="small-label">ABOUT THIS STORY</span><h2>故事简介</h2></div>{anime.sourceUrl && <a href={anime.sourceUrl} target="_blank" rel="noreferrer">Bangumi 资料 ↗</a>}</div><div className="watch-tags"><span>{anime.year}</span>{anime.tags?.map((tag) => <span key={tag}>{tag}</span>)}<span>全 {anime.episodes} 集</span></div><p className={`watch-synopsis${expanded ? " is-expanded" : ""}`}>{anime.synopsis || anime.description}</p><button className="text-button" type="button" onClick={() => setExpanded((previous) => !previous)} aria-expanded={expanded}>{expanded ? "收起简介 ↑" : "展开简介 ↓"}</button></section><aside className="related-panel"><h2>下一个心动故事</h2>{relatedAnime.map((item) => <Link className="related-item" key={item.id} href={`/anime/${item.id}`}><div className="related-cover"><Image src={item.cover} alt="" fill sizes="66px" /></div><div><strong>{item.title}</strong><span>{item.category}</span><small>全 {item.episodes} 集</small></div><i>›</i></Link>)}</aside></div>
  </div>;
}
