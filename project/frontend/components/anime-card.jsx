import Link from "next/link";
import AnimePoster from "./anime-poster";
import FavoriteButton from "./favorite-button";

export default function AnimeCard({ anime, number, onBeforeToggle }) {
  return (
    <article className="anime-card">
      <Link className="poster-link" href={`/anime/${anime.id}`} aria-label={`查看《${anime.title}》详情`}>
        <AnimePoster anime={anime} number={number} />
      </Link>
      <div className="card-body">
        <p className="card-meta">{anime.category}</p>
        <h3><Link className="title-link" href={`/anime/${anime.id}`}>{anime.title}</Link></h3>
        <p className="card-description">{anime.description}</p>
        <div className="card-bottom">
          <span className="episode-count">全 {anime.episodes} 集 · 演示条目</span>
          <FavoriteButton animeId={anime.id} title={anime.title} onBeforeToggle={onBeforeToggle} />
        </div>
      </div>
    </article>
  );
}
