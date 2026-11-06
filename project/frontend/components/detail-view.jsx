"use client";
import Image from "next/image";
import Link from "next/link";

import { useState } from "react";
import useApi from "../lib/use-api";
import ContinueWatching from "./continue-watching";
import FavoriteButton from "./favorite-button";
import { CollectionStatusPicker } from "./collection-provider";

export default function DetailView({ anime: initialAnime, initialSource }) {
  const { data, error, loading, retry } = useApi(
    `/api/catalog/${initialAnime.id}`,
  );
  const anime = data || initialAnime;
  const [group, setGroup] = useState(0);
  const [expanded, setExpanded] = useState(false);

  const count = anime.episodes || 1;
  function watch(episode = 1) {
    return `/watch/${anime.id}?episode=${episode}${initialSource ? `&provider=anich&source=${initialSource}` : ""}`;
  }

  return (
    <div className="content-shell portal-detail">
      <nav className="breadcrumbs" aria-label="当前位置">
        <Link prefetch={false} href="/browse">
          番剧索引
        </Link>
        <span>›</span>
        <strong>{anime.title}</strong>
      </nav>
      {(anime.detailWarning ||
        error ||
        (loading && !initialAnime.detailComplete)) && (
        <p className="detail-cache-note" role="status">
          {error
            ? "完整资料暂未更新，已显示缓存资料。"
            : anime.detailWarning || "已显示缓存资料，正在补充详情…"}
          {error && (
            <button className="text-button" type="button" onClick={retry}>
              重新获取详情
            </button>
          )}
        </p>
      )}
      <section className="series-overview" aria-labelledby="series-title">
        <div className="series-cover">
          <Image
            src={anime.cover}
            alt={`${anime.title}海报`}
            fill
            loading="eager"
            fetchPriority="high"
            sizes="(max-width:540px) 140px, 220px"
          />
        </div>
        <div className="series-summary">
          <div className="series-meta-line">
            <span>{anime.platform || "动画"}</span>
            <span>{anime.year || "年份待定"}</span>
            <span>{anime.episodes ? `${anime.episodes} 集` : "集数待定"}</span>
          </div>
          <h1 id="series-title">{anime.title}</h1>
          <p className="series-original">{anime.originalTitle}</p>
          <div className="detail-tags">
            {anime.tags?.slice(0, 8).map((tag) => (
              <Link
                prefetch={false}
                key={tag}
                href={`/browse?genre=${encodeURIComponent(tag)}`}
              >
                {tag}
              </Link>
            ))}
          </div>
          <p className="series-description">{anime.description}</p>
          <div className="series-actions">
            <Link prefetch={false} className="solid-button" href={watch()}>
              前往播放 →
            </Link>
            <ContinueWatching animeId={anime.id} />
            <CollectionStatusPicker anime={anime} />
            <FavoriteButton animeId={anime.id} title={anime.title} />
          </div>
          <p className="series-air-date">
            首播 {anime.releaseDate || "待定"} · 资料与视频来源分别提供
          </p>
        </div>
        <aside className="series-rating">
          <span>Bangumi 评分</span>
          <strong>{anime.score > 0 ? anime.score.toFixed(1) : "—"}</strong>
          <small>
            {anime.ratingCount
              ? `${anime.ratingCount.toLocaleString()} 人评分`
              : "暂无评分人数"}
          </small>
          {anime.rank > 0 && <b>排名 #{anime.rank}</b>}
          <a href={anime.sourceUrl} target="_blank" rel="noreferrer">
            查看原条目 ↗
          </a>
        </aside>
      </section>
      <div className="series-content">
        <div className="series-main">
          <section className="series-section" aria-labelledby="series-synopsis">
            <h2 id="series-synopsis">剧情简介</h2>
            <p className={`series-synopsis${expanded ? " is-expanded" : ""}`}>
              {anime.synopsis || "暂无简介"}
            </p>
            {anime.synopsis?.length > 250 && (
              <button
                className="text-button"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? "收起" : "展开全部"}
              </button>
            )}
          </section>
          <section className="series-section" aria-labelledby="series-episodes">
            <div className="portal-section-heading">
              <div>
                <h2 id="series-episodes">剧集</h2>
                <span>
                  {anime.episodes
                    ? `全 ${anime.episodes} 集`
                    : "资料尚未确认总集数"}
                </span>
              </div>
              {count > 50 && (
                <select
                  aria-label="剧集范围"
                  value={group}
                  onChange={(event) => setGroup(Number(event.target.value))}
                >
                  {Array.from({ length: Math.ceil(count / 50) }, (_, i) => (
                    <option value={i} key={i}>
                      {i * 50 + 1}–{Math.min(count, (i + 1) * 50)} 集
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="series-episode-grid">
              {Array.from(
                { length: Math.max(0, Math.min(50, count - group * 50)) },
                (_, i) => group * 50 + i + 1,
              ).map((episode) => (
                <Link prefetch={false} key={episode} href={watch(episode)}>
                  第 {String(episode).padStart(2, "0")} 集<span>▷</span>
                </Link>
              ))}
            </div>
            <p className="series-resource-note">
              集数来自番剧资料。实际可播集数与线路以匹配后的来源为准。
            </p>
          </section>
          <section
            className="series-section"
            aria-labelledby="series-production"
          >
            <h2 id="series-production">制作信息</h2>
            {anime.aliases && (
              <div className="series-aliases">
                <span>别名</span>
                <p>{anime.aliases}</p>
              </div>
            )}
            <dl className="series-staff">
              {anime.staff?.length ? (
                anime.staff.map((item) => (
                  <div key={item.label}>
                    <dt>{item.label}</dt>
                    <dd>{item.value}</dd>
                  </div>
                ))
              ) : (
                <p>暂未取得更多制作信息，可前往 Bangumi 查看。</p>
              )}
            </dl>
          </section>
        </div>
      </div>
    </div>
  );
}
