import Link from "next/link";
import AnimePoster from "./anime-poster";
import FavoriteButton from "./favorite-button";
export default function AnimeCard({ anime, onBeforeToggle }) {
  return (
    <article className="anime-card">
      <Link className="poster-link" href={`/anime/${anime.id}`} aria-label={`查看《${anime.title}》详情`}><AnimePoster anime={anime} /><span className="poster-open" aria-hidden="true">▶</span></Link>
      <div className="card-body"><p className="card-meta">{anime.year || "演示"}<span>·</span>{anime.tags?.[0] || "动画"}</p><h3><Link className="title-link" href={`/anime/${anime.id}`}>{anime.title}</Link></h3><p className="card-description">{anime.category}</p><div className="card-bottom"><span className="episode-count">{anime.isDemo ? "演示资料" : "Bangumi 资料"}</span><FavoriteButton animeId={anime.id} title={anime.title} onBeforeToggle={onBeforeToggle} /></div></div>
    </article>
  );
}
