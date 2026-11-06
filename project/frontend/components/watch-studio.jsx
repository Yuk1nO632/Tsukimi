"use client";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { animeList } from "../lib/anime";
import { readPlayback, rememberSource } from "../lib/playback-api";
import useWatchProgress from "../lib/use-watch-progress";
import { progressUrl } from "./continue-watching";
import { useAccount } from "./account-provider";
import FavoriteButton from "./favorite-button";
import MediaPlayer from "./media-player";
import SourceMatcher from "./source-matcher";
import PlayerIcon from "./player-icon";
import LineSelector from "./line-selector";

export default function WatchStudio({
  anime,
  selectedEpisode,
  selectedSourceId,
  selectedLineId,
}) {
  const account = useAccount();
  const [wide, setWide] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [retry, setRetry] = useState(0);
  const [copyMessage, setCopyMessage] = useState("");
  const [source, setSource] = useState({ status: "loading" });
  const progress = useWatchProgress(anime.id, selectedEpisode, source, !testMode);
  const helpRef = useRef(null);
  const sourcePanelRef = useRef(null);
  const matcherDetailsRef = useRef(null);
  const saveSourceController = useRef(null);
  const [selectingSource, setSelectingSource] = useState(false);
  const [sourceSaveError, setSourceSaveError] = useState("");
  const sourceInputRef = useRef(null);
  const router = useRouter();
  const relatedAnime = animeList
    .filter((item) => item.id !== anime.id)
    .slice(0, 3);

  useEffect(() => () => saveSourceController.current?.abort(), []);

  useEffect(() => {
    if (testMode || !account.ready) return;
    const controller = new AbortController();
    setSource({ status: "loading" });
    readPlayback(
      anime.id,
      selectedEpisode,
      selectedSourceId,
      selectedLineId,
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) setSource(data);
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setSource({
            status: "error",
            message: error.message || "来源暂时无法读取，请重试。",
          });
      });
    return () => controller.abort();
  }, [
    account.ready,
    anime.id,
    selectedEpisode,
    selectedSourceId,
    selectedLineId,
    retry,
    testMode,
  ]);
  useEffect(() => {
    if (!copyMessage) return;
    const timer = window.setTimeout(() => setCopyMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [copyMessage]);

  useEffect(() => {
    function closeHelp(event) {
      const help = helpRef.current;
      if (
        help?.open &&
        (event.key === "Escape" ||
          (event.type === "pointerdown" && !help.contains(event.target)))
      )
        help.open = false;
    }
    document.addEventListener("pointerdown", closeHelp);
    document.addEventListener("keydown", closeHelp);
    return () => {
      document.removeEventListener("pointerdown", closeHelp);
      document.removeEventListener("keydown", closeHelp);
    };
  }, []);
  function episodeUrl(
    episode,
    sourceId = selectedSourceId || source.source_anime_id,
    lineId = source.line_id || selectedLineId,
  ) {
    const query = new URLSearchParams({
      episode: String(episode),
      provider: "anich",
    });
    if (sourceId) query.set("source", String(sourceId));
    if (lineId) query.set("line", String(lineId));
    return `/watch/${anime.id}?${query}`;
  }
  function findSource() {
    if (matcherDetailsRef.current) matcherDetailsRef.current.open = true;
    sourcePanelRef.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "center",
    });
    sourceInputRef.current?.focus({ preventScroll: true });
    sourceInputRef.current?.select();
  }
  async function chooseSource(id, item) {
    if (selectingSource) return;
    const controller = new AbortController();
    saveSourceController.current = controller;
    setSelectingSource(true);
    setSourceSaveError("");
    try {
      await rememberSource(anime.id, id, controller.signal);
      if (controller.signal.aborted) return;
      setTestMode(false);
      const episode =
        item?.episodes > 0 && selectedEpisode > item.episodes
          ? 1
          : selectedEpisode;
      router.push(episodeUrl(episode, id, null), { scroll: false });
    } catch (error) {
      if (controller.signal.aborted) return;
      setSourceSaveError(error.message || "无法记住来源选择，请重试。");
    } finally {
      if (!controller.signal.aborted) setSelectingSource(false);
    }
  }
  function nextLine() {
    const lines = source.lines || [];
    if (!lines.length) return;
    const index = lines.findIndex((line) => line.id === source.line_id);
    const next = lines[(index + 1) % lines.length];
    router.replace(
      episodeUrl(selectedEpisode, source.source_anime_id, next.id),
      { scroll: false },
    );
  }
  function reloadSource() {
    if (!testMode) setSource({ status: "loading" });
    setRetry((previous) => previous + 1);
  }
  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopyMessage("播放页链接已复制");
    } catch {
      setCopyMessage("复制未成功，请复制浏览器地址栏中的网址。");
    }
  }
  const media = testMode
    ? { status: "ready", url: "/media/flower.mp4", isTest: true }
    : progress.loading ? { status: "loading" } : source;
  const ready = source.status === "ready";
  const sourceLabel =
    source.status === "loading"
      ? "连接中"
      : ready
        ? source.match_kind === "automatic"
          ? "自动匹配"
          : source.match_kind === "saved"
            ? "已记住选择"
            : "已匹配"
        : "需要选择来源";
  const episodeCount =
    anime.episodes || source.episode_count || selectedEpisode;
  const nextHref =
    selectedEpisode < episodeCount ? episodeUrl(selectedEpisode + 1) : null;

  return (
    <div className="watch-page content-shell">
      <nav className="breadcrumbs" aria-label="当前位置">
        <Link prefetch={false} href="/">
          番剧频道
        </Link>
        <span>›</span>
        <Link prefetch={false} href={`/anime/${anime.id}`}>
          {anime.title}
        </Link>
        <span>›</span>
        <strong>正在观看</strong>
      </nav>
      <div className={`watch-stage${wide ? " is-wide" : ""}`}>
        <section className="player-column" aria-label="视频播放区域">
          <MediaPlayer
            key={`${testMode}:${retry}:${media.url || media.status}`}
            media={media}
            initialPosition={testMode ? 0 : progress.position}
            onProgress={testMode ? undefined : progress.report}
            globalKeyboard
            autoPlay={!testMode}
            label={
              testMode
                ? "MDN 播放器测试短片"
                : `${anime.title} · 第 ${selectedEpisode} 集`
            }
            wide={wide}
            onWide={() => setWide((previous) => !previous)}
            onRetry={reloadSource}
            onFindSource={findSource}
            onNextLine={
              !testMode && source.lines?.length > 1 ? nextLine : undefined
            }
            nextHref={nextHref}
          />
          {!testMode && <div className={`watch-progress-status${progress.error ? " has-error" : ""}`} role="status">
            <span>{progress.message}</span>
            {progress.conflict ? <div>
              <button className="text-button" onClick={() => { window.location.assign(progressUrl(progress.conflict)); }}>使用云端进度</button>
              <button className="text-button" onClick={progress.keepLocal}>以本机进度继续</button>
            </div> : progress.error && <button className="text-button" onClick={progress.retry}>重试同步</button>}
          </div>}
          <div className="watch-now">
            <div>
              <span className="watch-now-kicker">
                {testMode ? "播放器测试" : "正在观看"}
              </span>
              <h2>
                {anime.title}
                <span>第 {String(selectedEpisode).padStart(2, "0")} 集</span>
              </h2>
            </div>
            <button type="button" className="watch-share" onClick={copyLink}>
              复制链接 ↗
            </button>
          </div>
          <div className="watch-episode-navigation">
            {selectedEpisode > 1 ? (
              <Link
                prefetch={false}
                scroll={false}
                href={episodeUrl(selectedEpisode - 1)}
              >
                ← 上一集
              </Link>
            ) : (
              <button type="button" disabled>
                ← 上一集
              </button>
            )}
            <span>
              第 {selectedEpisode} 集 / 全 {episodeCount} 集
            </span>
            {nextHref ? (
              <Link
                prefetch={false}
                className="next-episode-link"
                scroll={false}
                href={nextHref}
              >
                下一集 <PlayerIcon name="next" size={15} />
              </Link>
            ) : (
              <button type="button" disabled>
                已是最后一集
              </button>
            )}
          </div>
          <div className="watch-assist">
            <span className="playback-origin">
              {testMode
                ? "测试短片 · 非番剧正片"
                : ready
                  ? `AniCh · ${source.episode_title || `第 ${selectedEpisode} 集`}`
                  : source.status === "loading"
                    ? "正在自动查找并加载播放来源…"
                    : "请确认对应的播放来源"}
            </span>
            <details className="playback-help" ref={helpRef}>
              <summary>播放帮助</summary>
              <div>
                <p>
                  点击画面播放 / 暂停，双击全屏。快捷键：空格播放 / 暂停，← →
                  跳转 5 秒，↑ ↓ 调节音量，M 静音，F 全屏。
                </p>
                <p>播放时控制栏会自动收起，移动鼠标或触碰画面即可唤回。</p>
                <button
                  type="button"
                  onClick={() => {
                    if (helpRef.current) helpRef.current.open = false;
                    setTestMode((previous) => !previous);
                  }}
                >
                  {testMode ? "返回番剧来源" : "试播测试短片"}
                </button>
              </div>
            </details>
          </div>
          {testMode && (
            <div className="test-mode-banner">
              当前是约 5 秒的播放器测试短片。
              <button type="button" onClick={() => setTestMode(false)}>
                返回番剧正片 →
              </button>
            </div>
          )}
          {copyMessage && (
            <p className="watch-copy-feedback" role="status">
              {copyMessage}
            </p>
          )}
        </section>
        <aside className="watch-sidebar" aria-labelledby="watch-anime-title">
          <div className="watch-series-card">
            <Link
              prefetch={false}
              className="watch-series-cover"
              href={`/anime/${anime.id}`}
            >
              <Image src={anime.cover} alt="" fill sizes="76px" />
            </Link>
            <div>
              <span className="small-label">番剧 · {anime.year}</span>
              <h1 id="watch-anime-title">
                <Link prefetch={false} href={`/anime/${anime.id}`}>
                  {anime.title}
                </Link>
              </h1>
              <p>{anime.category}</p>
              {anime.score > 0 && (
                <span className="inline-rating">
                  {anime.score.toFixed(1)} <small>Bangumi</small>
                </span>
              )}
            </div>
          </div>
          <div className="watch-save-row">
            <FavoriteButton animeId={anime.id} title={anime.title} />
            <Link prefetch={false} href={`/anime/${anime.id}`}>
              作品详情 →
            </Link>
          </div>
          <section
            className={`watch-source-panel${!ready ? " needs-source" : ""}`}
            ref={sourcePanelRef}
            aria-labelledby="source-panel-title"
          >
            <div className="source-panel-heading">
              <h2 id="source-panel-title">
                播放来源 <span>AniCh</span>
              </h2>
              <span className={`source-badge${ready ? " is-ready" : ""}`}>
                <i />
                {sourceLabel}
              </span>
            </div>
            <details
              className="watch-source-tools"
              ref={matcherDetailsRef}
              open={source.status === "unmatched"}
            >
              <summary>
                {source.status === "unmatched"
                  ? "确认播放来源"
                  : "更换来源 / 匹配有误？"}
              </summary>
              <SourceMatcher
                title={anime.title}
                inputRef={sourceInputRef}
                selectedId={source.source_anime_id}
                initialItems={source.candidates}
                selecting={selectingSource}
                onSelect={chooseSource}
              />
              {sourceSaveError && (
                <p className="source-save-error" role="alert">
                  {sourceSaveError}
                </p>
              )}
            </details>
            {ready && (
              <div className="source-current">
                <span>当前作品</span>
                <strong>{source.source_title}</strong>
              </div>
            )}
            {source.lines?.length > 0 && (
              <LineSelector
                context={`${anime.id}:${selectedEpisode}`}
                lines={source.lines}
                selectedId={source.line_id}
                disabled={testMode}
                onSelect={(id) =>
                  router.replace(
                    episodeUrl(selectedEpisode, source.source_anime_id, id),
                    { scroll: false },
                  )
                }
              />
            )}
            <div className="source-panel-actions">
              <button
                type="button"
                disabled={source.status === "loading" || testMode}
                onClick={reloadSource}
              >
                <PlayerIcon name="refresh" size={13} />
                重新连接
              </button>
              {source.source_page && (
                <a href={source.source_page} target="_blank" rel="noreferrer">
                  前往来源站 ↗
                </a>
              )}
            </div>
          </section>
          <section
            className="watch-episodes-panel"
            aria-labelledby="episodes-title"
          >
            <div className="episode-selector-heading">
              <h2 id="episodes-title">选集</h2>
              <span>全 {episodeCount} 集</span>
            </div>
            <div className="episode-selector" aria-label="选集列表">
              {Array.from({ length: episodeCount }, (_, index) => (
                <Link
                  prefetch={false}
                  key={index + 1}
                  scroll={false}
                  href={episodeUrl(index + 1)}
                  aria-current={
                    selectedEpisode === index + 1 ? "page" : undefined
                  }
                  aria-label={`选择第 ${index + 1} 集`}
                >
                  {String(index + 1).padStart(2, "0")}
                  {selectedEpisode === index + 1 && (
                    <span className="episode-playing" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                  )}
                </Link>
              ))}
            </div>
          </section>
        </aside>
      </div>
      <div className="watch-below">
        <section className="watch-information">
          <div className="watch-title-row">
            <div>
              <span className="small-label">ABOUT THIS STORY</span>
              <h2>故事简介</h2>
            </div>
            {anime.sourceUrl && (
              <a href={anime.sourceUrl} target="_blank" rel="noreferrer">
                Bangumi 资料 ↗
              </a>
            )}
          </div>
          <div className="watch-tags">
            <span>{anime.year}</span>
            {anime.tags?.map((tag) => (
              <span key={tag}>{tag}</span>
            ))}
            <span>全 {episodeCount} 集</span>
          </div>
          <p className={`watch-synopsis${expanded ? " is-expanded" : ""}`}>
            {anime.synopsis || anime.description}
          </p>
          <button
            className="text-button"
            type="button"
            onClick={() => setExpanded((previous) => !previous)}
            aria-expanded={expanded}
          >
            {expanded ? "收起简介 ↑" : "展开简介 ↓"}
          </button>
        </section>
        <aside className="related-panel">
          <h2>其他番剧</h2>
          {relatedAnime.map((item) => (
            <Link
              prefetch={false}
              className="related-item"
              key={item.id}
              href={`/anime/${item.id}`}
            >
              <div className="related-cover">
                <Image src={item.cover} alt="" fill sizes="66px" />
              </div>
              <div>
                <strong>{item.title}</strong>
                <span>{item.category}</span>
                <small>全 {item.episodes} 集</small>
              </div>
              <i>›</i>
            </Link>
          ))}
        </aside>
      </div>
    </div>
  );
}
