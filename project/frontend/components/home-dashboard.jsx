"use client";
import Image from "next/image";
import Link from "next/link";
import { animeList } from "../lib/anime";
import { currentSeason, genres } from "../lib/catalog-params";
import useApi from "../lib/use-api";
import AnimeCard from "./anime-card";
import FeaturedHero from "./featured-hero";
import CalendarBoard from "./calendar-board";
import HomeSeasonRanking from "./home-season-ranking";
import HomeCollections from "./home-collections";
import HomeSpotlight from "./home-spotlight";
import { collectionLabels, useCollection } from "./collection-provider";
import { LoadFailure, SkeletonGrid } from "./portal-state";

const seasonNames = ["冬季", "春季", "夏季", "秋季"];
export default function HomeDashboard() {
  const { year, season } = currentSeason();
  const { data, error, loading, retry } = useApi(
    `/api/catalog?year=${year}&season=${season}&sort=heat&limit=12`,
  );
  const { collectionItems, status } = useCollection();
  const classics = animeList
    .filter((anime) => Number(anime.year) < year)
    .slice(0, 6);
  const seasonItems = data?.items || [];
  const seasonUrl = `/browse?year=${year}&season=${season}&sort=heat`;
  const libraryStats = [
    ["全部", collectionItems.length],
    ...Object.entries(collectionLabels).map(([value, label]) => [
      label,
      collectionItems.filter((item) => item.status === value).length,
    ]),
  ];
  return (
    <>
      <div className="channel-heading content-shell">
        <div>
          <h2>番剧频道</h2>
          <span>新番 · 榜单 · 放送安排</span>
        </div>
        <span className="channel-season-pill">
          <i aria-hidden="true" />
          {year} · {seasonNames[season - 1]}新番
        </span>
      </div>
      <div className="home-feature-layout content-shell">
        {loading ? (
          <div className="home-hero-loading" role="status">
            正在加载 {year} 年 {season * 3 - 2} 月新番…
          </div>
        ) : error ? (
          <div className="home-hero-loading">
            <LoadFailure error={error} retry={retry} />
          </div>
        ) : !seasonItems.length ? (
          <div className="home-hero-loading home-hero-empty">
            <h3>本季番剧资料暂未收录</h3>
            <Link prefetch={false} className="outline-button" href="/browse">
              浏览番剧索引 →
            </Link>
          </div>
        ) : (
          <FeaturedHero
            items={seasonItems.slice(0, 3)}
            seasonLabel={`${year} · ${season * 3 - 2}月新番`}
          />
        )}
        <HomeSeasonRanking
          items={seasonItems}
          loading={loading}
          error={error}
          retry={retry}
          seasonUrl={seasonUrl}
        />
      </div>
      <div className="content-shell home-portal">
        <nav className="home-category-nav" aria-label="番剧类型快捷浏览">
          <strong>分类浏览</strong>
          <div className="home-category-links">
            {genres.map((genre) => (
              <Link
                prefetch={false}
                key={genre}
                href={`/browse?${new URLSearchParams({ genre, sort: "heat" })}`}
              >
                {genre}
              </Link>
            ))}
          </div>
          <Link prefetch={false} href="/browse">
            全部分类 ↗
          </Link>
        </nav>
        <nav className="home-shortcuts" aria-label="频道入口">
          <Link prefetch={false} href={seasonUrl}>
            <strong>本季新番</strong>
            <span>
              {year} 年 {season * 3 - 2} 月 →
            </span>
          </Link>
          <Link prefetch={false} href="/browse">
            <strong>番剧索引</strong>
            <span>年份 · 季度 · 类型 →</span>
          </Link>
          <Link prefetch={false} href="/calendar">
            <strong>放送日历</strong>
            <span>每周放送安排 →</span>
          </Link>
          <Link prefetch={false} href="/collection">
            <strong>我的追番</strong>
            <span>
              {status === "ready"
                ? `${collectionItems.length} 部已加入片单`
                : "读取片单中"}{" "}
              →
            </span>
          </Link>
        </nav>
        <HomeSpotlight items={classics.slice(0, 4)} />
        <section className="home-section" aria-labelledby="home-season-title">
          <div className="portal-section-heading">
            <div>
              <h2 id="home-season-title">本季新番</h2>
              <span>按 Bangumi 收藏热度排序</span>
            </div>
            <Link prefetch={false} href={seasonUrl}>
              查看全部 →
            </Link>
          </div>
          {loading ? (
            <SkeletonGrid count={6} />
          ) : error ? (
            <LoadFailure error={error} retry={retry} />
          ) : seasonItems.length ? (
            <div className="anime-grid portal-grid">
              {seasonItems.map((anime) => (
                <AnimeCard key={anime.id} anime={anime} />
              ))}
            </div>
          ) : (
            <div className="portal-empty">
              <h3>暂无本季番剧资料</h3>
              <Link className="outline-button" href="/browse" prefetch={false}>
                浏览番剧资料库
              </Link>
            </div>
          )}
        </section>
        <section
          className="home-collection-strip"
          aria-labelledby="home-collection-title"
        >
          <div className="home-library-header">
            <div className="portal-section-heading">
              <div>
                <h2 id="home-collection-title">我的追番</h2>
                <span>想看、在看、看完，统一管理</span>
              </div>
              <Link prefetch={false} href="/collection">
                管理片单 →
              </Link>
            </div>
            <dl className="home-library-summary" aria-label="我的片单状态概览">
              {libraryStats.map(([label, count]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{status === "ready" ? count : "—"}</dd>
                </div>
              ))}
            </dl>
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
                <Link
                  prefetch={false}
                  key={anime.id}
                  href={`/anime/${anime.id}`}
                >
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
              <Link prefetch={false} href="/browse">
                添加番剧 ＋
              </Link>
            </div>
          )}
        </section>
        <HomeCollections classics={classics} />
        <section className="home-section" aria-labelledby="home-calendar-title">
          <div className="portal-section-heading">
            <div>
              <h2 id="home-calendar-title">放送日历</h2>
              <span>当前在播动画</span>
            </div>
            <Link prefetch={false} href="/calendar">
              完整日历 →
            </Link>
          </div>
          <CalendarBoard compact />
        </section>
        <section className="home-section" aria-labelledby="home-classics-title">
          <div className="portal-section-heading">
            <div>
              <h2 id="home-classics-title">经典回看</h2>
              <span>已收录的完结作品</span>
            </div>
            <Link prefetch={false} href="/browse?sort=heat">
              更多热门番剧 →
            </Link>
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
