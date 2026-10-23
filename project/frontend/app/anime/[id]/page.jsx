import Link from "next/link";
import { notFound } from "next/navigation";
import { getAllAnimeIds, getAnime } from "../../../lib/anime";
import AnimePoster from "../../../components/anime-poster";
import FavoriteButton from "../../../components/favorite-button";
export const dynamicParams = false;
export function generateStaticParams() { return getAllAnimeIds().map((id) => ({ id })); }
export async function generateMetadata({ params }) {
  const { id } = await params;
  return { title: getAnime(id)?.title || "未找到番剧" };
}
export default async function AnimeDetailPage({ params }) {
  const { id } = await params;
  const anime = getAnime(id);
  if (!anime) notFound();
  return (
    <div className="detail-page content-shell">
      <nav className="breadcrumbs" aria-label="当前位置"><Link href="/">番剧</Link><span>›</span><strong>{anime.title}</strong></nav>
      <section className="detail-overview" aria-labelledby="anime-title"><div className="detail-poster"><AnimePoster anime={anime} /></div><div className="detail-copy"><span className="demo-badge">{anime.isDemo ? "旧版演示条目" : "真实番剧资料"}</span><h1 id="anime-title">{anime.title}</h1><p className="original-title">{anime.originalTitle || "Tsukimi Originals"}</p><div className="detail-tags">{anime.tags?.map((tag) => <span key={tag}>{tag}</span>)}</div><p className="detail-description">{anime.description}</p><dl className="anime-facts"><div><dt>集数</dt><dd>全 {anime.episodes} 集</dd></div><div><dt>首播</dt><dd>{anime.releaseDate || "演示日期"}</dd></div>{anime.score > 0 && <div><dt>Bangumi</dt><dd className="inline-rating">{anime.score.toFixed(1)} <small>分 · 资料缓存评分</small></dd></div>}</dl><div className="detail-actions"><Link className="primary-link" href={`/watch/${anime.id}`}><span aria-hidden="true">▷</span> 查看播放页</Link><FavoriteButton animeId={anime.id} title={anime.title} /></div>{anime.sourceUrl && <a className="detail-source-link" href={anime.sourceUrl} target="_blank" rel="noreferrer">资料来自 Bangumi · 查看原条目 ↗</a>}</div></section>
      <section className="detail-section" aria-labelledby="synopsis-title"><h2 id="synopsis-title">故事简介</h2><p className="synopsis">{anime.synopsis || anime.description}</p></section>
      <section className="detail-section" aria-labelledby="episodes-title"><div className="section-heading"><div className="section-title"><h2 id="episodes-title">全部剧集</h2><span className="section-subtitle">全 {anime.episodes} 集</span></div><span className="unavailable-label">视频来源待接入</span></div><div className="episode-grid">{Array.from({ length: anime.episodes }, (_, index) => <Link className="episode-link" href={`/watch/${anime.id}?episode=${index + 1}`} key={index + 1}><span>第 {String(index + 1).padStart(2, "0")} 集</span><span aria-hidden="true">▷</span></Link>)}</div><p className="demo-caption">选集可进入播放页；目前只有番剧资料，尚未接入可播放的视频来源。</p></section>
    </div>
  );
}
