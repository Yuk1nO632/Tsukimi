"use client";

import Image from "next/image";
import Link from "next/link";
import useApi from "../lib/use-api";
import AnimeCard from "./anime-card";
import { selectPopularPicks } from "../lib/discovery";
import { LoadFailure, SkeletonGrid } from "./portal-state";

const themes = ["奇幻", "科幻", "音乐", "治愈", "悬疑", "恋爱"];

function hasGenre(anime, genre) {
  return (
    anime.tags?.includes(genre) ||
    String(anime.category || "")
      .split(/\s*[\/·、]\s*/)
      .includes(genre)
  );
}

export default function HomeCollections({ classics = [] }) {
  const { data, error, loading, retry } = useApi(
    "/api/catalog?sort=heat&limit=18",
  );
  const rated = selectPopularPicks(data?.items);
  const selected = new Set();
  const collections = themes.map((genre) => {
    const matching = classics.filter((anime) => hasGenre(anime, genre));
    const anime =
      matching.find((item) => !selected.has(item.id)) || matching[0];
    if (anime) selected.add(anime.id);
    return { genre, anime };
  });

  return (
    <>
      <section
        className="home-section discovery-section score-discovery"
        aria-labelledby="home-score-title"
      >
        <div className="portal-section-heading">
          <div>
            <h2 id="home-score-title">高分发现</h2>
            <span>热门作品 · 千人评分筛选</span>
          </div>
          <Link prefetch={false} href="/browse?sort=heat">
            更多热门 →
          </Link>
        </div>
        {loading ? (
          <SkeletonGrid count={6} />
        ) : error ? (
          <LoadFailure error={error} retry={retry} />
        ) : rated.length ? (
          <div className="anime-grid portal-grid">
            {rated.map((anime) => (
              <div className="popular-pick" key={anime.id}>
                <AnimeCard anime={anime} />
                <p className="popular-pick-evidence">
                  {anime.ratingCount.toLocaleString("zh-CN")} 人评分
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="portal-empty">
            <h3>暂时没有符合条件的高分条目</h3>
            <Link
              className="outline-button"
              prefetch={false}
              href="/browse?sort=heat"
            >
              查看番剧索引
            </Link>
          </div>
        )}
      </section>
      <section
        className="home-section discovery-section"
        aria-labelledby="home-genres-title"
      >
        <div className="portal-section-heading">
          <div>
            <h2 id="home-genres-title">按类型发现</h2>
            <span>按题材浏览番剧</span>
          </div>
          <Link prefetch={false} href="/browse">
            全部类型 →
          </Link>
        </div>
        <div className="genre-collection-grid">
          {collections.map(({ genre, anime }) => {
            const query = new URLSearchParams({ genre, sort: "heat" });
            return (
              <Link
                className="genre-collection"
                prefetch={false}
                href={`/browse?${query}`}
                key={genre}
                aria-label={`浏览${genre}番剧`}
              >
                {anime?.cover && (
                  <span className="genre-collection-cover">
                    <Image
                      src={anime.cover}
                      alt=""
                      fill
                      sizes="(max-width: 540px) 64px, 86px"
                    />
                  </span>
                )}
                <span className="genre-collection-copy">
                  <strong>{genre}</strong>
                  <span>{anime?.title || `${genre}题材`}</span>
                  <small>
                    {anime
                      ? `${anime.year} · ${anime.platform || "动画"}`
                      : "按收藏热度浏览"}
                  </small>
                  <em>浏览同类番剧 →</em>
                </span>
              </Link>
            );
          })}
        </div>
      </section>
    </>
  );
}
