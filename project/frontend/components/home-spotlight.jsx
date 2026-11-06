"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { readPlayback } from "../lib/playback-api";
import FavoriteButton from "./favorite-button";
import PlayerIcon from "./player-icon";

function PlayerLoadFailure({ onFindSource }) {
  return (
    <div className="spotlight-preview-state" role="alert">
      <h3>播放组件暂时无法载入</h3>
      <button type="button" onClick={onFindSource}>
        进入播放页 →
      </button>
    </div>
  );
}

const loadPreviewPlayer = () => import("./media-player");

const PreviewPlayer = dynamic(
  () => loadPreviewPlayer().catch(() => ({ default: PlayerLoadFailure })),
  {
    ssr: false,
    loading: () => (
      <div className="spotlight-preview-state" role="status">
        正在加载播放器…
      </div>
    ),
  },
);

function SpotlightPreview({ anime }) {
  const shellRef = useRef(null);
  const router = useRouter();
  const [inView, setInView] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const [started, setStarted] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [source, setSource] = useState({ status: "idle" });
  const active = inView && pageVisible;
  const watchHref = `/watch/${anime.id}?episode=1`;

  useEffect(() => {
    const element = shellRef.current;
    const observer = new IntersectionObserver(
      ([entry]) =>
        setInView(entry.isIntersecting && entry.intersectionRatio >= 0.5),
      { threshold: [0, 0.5] },
    );
    observer.observe(element);
    const prepare = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          void loadPreviewPlayer().catch(() => {});
          prepare.disconnect();
        }
      },
      { rootMargin: "240px 0px" },
    );
    prepare.observe(element);
    const visibility = () => setPageVisible(!document.hidden);
    visibility();
    document.addEventListener("visibilitychange", visibility);
    return () => {
      observer.disconnect();
      prepare.disconnect();
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  useEffect(() => {
    if (active) setStarted(true);
  }, [active]);

  useEffect(() => {
    if (!started) return;
    void loadPreviewPlayer().catch(() => {});
    const controller = new AbortController();
    setSource({ status: "loading" });
    readPlayback(anime.id, 1, null, null, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted)
          setSource(
            data.status === "ready" && !data.url
              ? { status: "unavailable" }
              : data,
          );
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setSource({ status: "error", message: error.message });
      });
    return () => controller.abort();
  }, [anime.id, started, attempt]);

  function retryPreview() {
    setStarted(true);
    setAttempt((previous) => previous + 1);
  }

  const ready = source.status === "ready" && !!source.url;
  const idle = source.status === "idle";
  const loading = source.status === "loading";

  return (
    <div
      className="spotlight-media"
      ref={shellRef}
      aria-label={`${anime.title}第一集预览`}
    >
      {ready ? (
        <PreviewPlayer
          key={`${attempt}:${source.url}`}
          media={source}
          label={`${anime.title} · 第 1 集`}
          autoPlay
          initialMuted
          active={active}
          onRetry={retryPreview}
          onFindSource={() => router.push(watchHref)}
        />
      ) : (
        <div className="spotlight-loading-stage">
          <span className="spotlight-episode">第 1 集</span>
          <div
            className="spotlight-preview-state"
            role={idle || loading ? "status" : "alert"}
          >
            {idle ? (
              <button
                className="spotlight-start"
                type="button"
                onClick={retryPreview}
                aria-label={`播放《${anime.title}》第1集`}
              >
                <PlayerIcon name="play" size={27} />
              </button>
            ) : loading ? (
              <>
                <span className="spotlight-loading-ring" aria-hidden="true" />
                <p>正在加载第一集…</p>
              </>
            ) : (
              <>
                <h3>
                  {source.status === "unmatched"
                    ? "需要确认这部番剧的来源"
                    : "这一集暂时无法预览"}
                </h3>
                <p>
                  {source.message || "可以进入播放页选择来源，或稍后重试。"}
                </p>
                <div className="spotlight-preview-actions">
                  <button type="button" onClick={retryPreview}>
                    重新加载
                  </button>
                  <Link prefetch={false} href={watchHref}>
                    进入播放页 →
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HomeSpotlight({ items = [] }) {
  const selectionsRef = useRef(null);
  const [selectedId, setSelectedId] = useState(items[0]?.id);
  const selected = items.find((anime) => anime.id === selectedId) || items[0];
  useEffect(() => {
    const rail = selectionsRef.current;
    const button = rail?.querySelector('[aria-pressed="true"]');
    if (!button) return;
    const revealSelection = () => rail.scrollTo({
      left: button.offsetLeft - (rail.clientWidth - button.offsetWidth) / 2,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
    revealSelection();
    const observer = new ResizeObserver(revealSelection);
    observer.observe(rail);
    return () => observer.disconnect();
  }, [selected?.id, items.length]);

  if (!selected) return null;
  const selectedIndex = items.findIndex((anime) => anime.id === selected.id);
  function move(offset) {
    setSelectedId(
      items[(selectedIndex + offset + items.length) % items.length].id,
    );
  }

  const score =
    Number.isFinite(selected.score) && selected.score > 0
      ? selected.score.toFixed(1)
      : null;

  return (
    <section
      className="home-section home-spotlight"
      aria-labelledby="home-spotlight-title"
    >
      <div className="portal-section-heading">
        <div>
          <h2 id="home-spotlight-title">新热推荐</h2>
          <span>精选番剧 · 第一集</span>
        </div>
        <Link prefetch={false} href="/browse?sort=heat">
          发现更多 →
        </Link>
      </div>
      <div className="spotlight-stage" data-tone={selectedIndex % 4}>
        <SpotlightPreview key={selected.id} anime={selected} />
        <div className="spotlight-info">
          <div className="spotlight-meta">
            <span>{selected.year || "动画"}</span>
            <i aria-hidden="true">·</i>
            <span>{selected.platform || "番剧"}</span>
            <i aria-hidden="true">·</i>
            <span>
              {selected.episodes > 0 ? `全 ${selected.episodes} 集` : "连载中"}
            </span>
          </div>
          <h3 className="spotlight-title">
            <Link prefetch={false} href={`/anime/${selected.id}`}>
              {selected.title}
            </Link>
          </h3>
          {score && (
            <div className="spotlight-rating">
              <strong>{score}</strong>
              <span>
                Bangumi 评分
                {selected.ratingCount > 0 && (
                  <small>
                    {selected.ratingCount.toLocaleString("zh-CN")} 人评分
                  </small>
                )}
              </span>
            </div>
          )}
          <p className="spotlight-summary">
            {selected.description || "暂无剧情简介"}
          </p>
          <div className="spotlight-actions">
            <Link
              className="spotlight-watch"
              prefetch={false}
              href={`/watch/${selected.id}?episode=1`}
            >
              <PlayerIcon name="play" size={17} />
              进入播放页
            </Link>
            <FavoriteButton animeId={selected.id} title={selected.title} />
          </div>
          <div
            className="spotlight-navigation"
            role="group"
            aria-label="推荐预览切换"
          >
            <span>
              {String(selectedIndex + 1).padStart(2, "0")} /{" "}
              {String(items.length).padStart(2, "0")}
            </span>
            <button
              type="button"
              onClick={() => move(-1)}
              aria-label="上一部推荐"
            >
              ← 上一部
            </button>
            <button
              type="button"
              onClick={() => move(1)}
              aria-label="下一部推荐"
            >
              下一部 →
            </button>
          </div>
          <div
            className="spotlight-selections"
            ref={selectionsRef}
            role="group"
            aria-label="切换新热推荐"
          >
            {items.map((anime) => (
              <button
                key={anime.id}
                type="button"
                aria-label={`推荐预览：${anime.title}`}
                aria-pressed={anime.id === selected.id}
                onClick={() => setSelectedId(anime.id)}
              >
                <span className="spotlight-thumb">
                  <Image
                    src={anime.cover}
                    alt=""
                    fill
                    sizes="(max-width: 540px) 25vw, 120px"
                  />
                  <span className="spotlight-selected-dot" aria-hidden="true" />
                </span>
                <span className="spotlight-thumb-title">{anime.title}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
