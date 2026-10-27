"use client";
import Image from "next/image";
import Link from "next/link";
import { animeList } from "../lib/anime";
import { currentSeason } from "../lib/catalog-params";
import useApi from "../lib/use-api";
import AnimeCard from "./anime-card";
import FeaturedHero from "./featured-hero";
import CalendarBoard from "./calendar-board";
import { collectionLabels, useCollection } from "./collection-provider";
import { LoadFailure, SkeletonGrid } from "./portal-state";

export default function HomeDashboard() {
  const { year, season } = currentSeason();
  const { data, error, loading, retry } = useApi(
    `/api/catalog?year=${year}&season=${season}&sort=heat&limit=12`,
  );
  const { collectionItems, status } = useCollection();
  const classics = animeList
    .filter((anime) => Number(anime.year) < year)
    .slice(0, 6);
  const seasonUrl = `/browse?year=${year}&season=${season}&sort=heat`;
  return (
    <>
      {loading ? (
        <div className="content-shell home-hero-loading" role="status">
          正在加载 {year} 年 {season * 3 - 2} 月新番…
        </div>
      ) : error ? (
        <div className="content-shell home-hero-loading">
          <LoadFailure error={error} retry={retry} />
        </div>
      ) : (
        <FeaturedHero
          items={data.items.slice(0, 3)}
          seasonLabel={`${year} · ${season * 3 - 2}月新番`}
        />
      )}
      <div className="content-shell home-portal">
        <nav className="home-shortcuts" aria-label="频道入口">
          <Link href={seasonUrl}>
            <strong>本季新番</strong>
            <span>
              {year} 年 {season * 3 - 2} 月 →
            </span>
          </Link>
          <Link href="/browse">
            <strong>番剧索引</strong>
            <span>年份 · 季度 · 类型 →</span>
          </Link>
          <Link href="/calendar">
            <strong>放送日历</strong>
            <span>每周放送安排 →</span>
          </Link>
          <Link href="/collection">
            <strong>我的追番</strong>
            <span>
              {status === "ready"
                ? `${collectionItems.length} 部已加入片单`
                : "读取片单中"}{" "}
              →
            </span>
          </Link>
        </nav>
        <section className="home-section" aria-labelledby="home-season-title">
          <div className="portal-section-heading">
            <div>
              <h2 id="home-season-title">本季新番</h2>
              <span>按 Bangumi 收藏热度排序</span>
            </div>
            <Link href={seasonUrl}>查看全部 →</Link>
          </div>
          {loading ? (
            <SkeletonGrid count={6} />
          ) : error ? (
            <LoadFailure error={error} retry={retry} />
          ) : (
            <div className="anime-grid portal-grid">
              {data.items.map((anime) => (
                <AnimeCard key={anime.id} anime={anime} />
              ))}
            </div>
          )}
        </section>
        <section
          className="home-collection-strip"
          aria-labelledby="home-collection-title"
        >
          <div className="portal-section-heading">
            <div>
              <h2 id="home-collection-title">我的追番</h2>
              <span>想看、在看、看完，统一管理</span>
            </div>
            <Link href="/collection">管理片单 →</Link>
          </div>
          {status !== "ready" ? (
            <p className="home-inline-note">
              {status === "loading"
                ? "正在读取片单…"
                : "片单暂时不可用，可在页面顶部重试。"}
            </p>
          ) : collectionItems.length ? (
            <div className="home-saved-list">
              {collectionItems.slice(0, 4).map(({ anime, status }) => (
                <Link key={anime.id} href={`/anime/${anime.id}`}>
                  <span className="home-saved-cover">
                    <Image src={anime.cover} alt="" fill sizes="58px" />
                  </span>
                  <span>
                    <strong>{anime.title}</strong>
                    <small>{collectionLabels[status]}</small>
                  </span>
                  <i>›</i>
                </Link>
              ))}
            </div>
          ) : (
            <div className="home-empty-collection">
              <p>尚未添加番剧。在详情页选择追番状态，即可加入片单。</p>
              <Link href="/browse">添加番剧 ＋</Link>
            </div>
          )}
        </section>
        <section className="home-section">
          <div className="portal-section-heading">
            <div>
              <h2>放送日历</h2>
              <span>当前在播动画</span>
            </div>
            <Link href="/calendar">完整日历 →</Link>
          </div>
          <CalendarBoard compact />
        </section>
        <section className="home-section">
          <div className="portal-section-heading">
            <div>
              <h2>经典回看</h2>
              <span>已收录的完结作品</span>
            </div>
            <Link href="/browse?sort=rank">更多高分番剧 →</Link>
          </div>
          <div className="anime-grid portal-grid">
            {classics.map((anime) => (
              <AnimeCard key={anime.id} anime={anime} />
            ))}
          </div>
        </section>
      </div>
    </>
  );
}
