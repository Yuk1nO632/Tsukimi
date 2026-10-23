import Link from "next/link";
import { notFound } from "next/navigation";
import { animeList, getAnime } from "../../../lib/anime";
import AnimePoster from "../../../components/anime-poster";
import FavoriteButton from "../../../components/favorite-button";

// [id] 是动态路由段，例如 /anime/forest。本阶段只开放演示条目的 id。
export const dynamicParams = false;
export function generateStaticParams() {
  return animeList.map((anime) => ({ id: anime.id }));
}

export async function generateMetadata({ params }) {
  const { id } = await params;
  const anime = getAnime(id);
  return { title: anime ? anime.title : "未找到番剧" };
}

export default async function AnimeDetailPage({ params }) {
  const { id } = await params;
  const anime = getAnime(id);
  if (!anime) notFound();
  const number = animeList.findIndex((item) => item.id === id) + 1;

  return (
    <div className="detail-page">
      <Link href="/" className="back-link">← 返回发现</Link>
      <section className="detail-overview" aria-labelledby="anime-title">
        <div className="detail-poster"><AnimePoster anime={anime} number={number} /></div>
        <div className="detail-copy">
          <span className="eyebrow">A STORY WORTH KEEPING</span>
          <span className="demo-badge">虚构演示番剧</span>
          <h1 id="anime-title">{anime.title}</h1>
          <p className="detail-description">{anime.description}</p>
          <dl className="anime-facts">
            <div><dt>分类</dt><dd>{anime.category}</dd></div>
            <div><dt>集数</dt><dd>全 {anime.episodes} 集</dd></div>
            <div><dt>每集时长</dt><dd>{anime.duration}</dd></div>
          </dl>
          <FavoriteButton animeId={anime.id} title={anime.title} />
        </div>
      </section>
      <section className="detail-section" aria-labelledby="synopsis-title">
        <span className="eyebrow">ABOUT THE STORY</span><h2 id="synopsis-title">故事简介</h2>
        <p className="synopsis">{anime.synopsis}</p>
      </section>
      <section className="detail-section" aria-labelledby="episodes-title">
        <div className="section-heading"><div><span className="eyebrow">EPISODE LIST</span><h2 id="episodes-title">剧集列表</h2></div><span className="unavailable-label">尚未接入播放来源</span></div>
        <div className="episode-grid">
          {Array.from({ length: anime.episodes }, (_, index) => (
            <div className="episode-placeholder" key={index + 1}><span>第 {String(index + 1).padStart(2, "0")} 集</span><span>暂无视频</span></div>
          ))}
        </div>
        <p className="demo-caption">这是演示集数，用于搭建详情页面；本阶段可以浏览和收藏，暂不提供视频播放。</p>
      </section>
    </div>
  );
}
