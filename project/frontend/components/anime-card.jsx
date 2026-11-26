import Link from "next/link";
import AnimePoster from "./anime-poster";
import FavoriteButton from "./favorite-button";
import { platformLabel, releaseLabel, searchPartLabel } from "../lib/catalog-display";

export default function AnimeCard({ anime, onToggleSuccess, searchDetails = false }) {
  const part = searchDetails ? searchPartLabel(anime) : "";
  const originalTitle =
    searchDetails && anime.originalTitle !== anime.title ? anime.originalTitle : "";

  return (
    <article className="anime-card">
      <Link
        prefetch={false}
        className="poster-link"
        href={"/anime/" + anime.id}
        aria-label={"查看《" + anime.title + "》详情"}
      >
        <AnimePoster anime={anime} />
        <span className="poster-open" aria-hidden="true">▶</span>
      </Link>
      <div className="card-body">
        <p className="card-meta" style={searchDetails ? { flexWrap: "wrap" } : undefined}>
          {searchDetails ? releaseLabel(anime) : anime.year || "演示"}
          <span aria-hidden="true">·</span>
          {searchDetails ? platformLabel(anime.platform) : anime.tags?.[0] || "动画"}
          {part && <><span aria-hidden="true">·</span>{part}</>}
        </p>
        <h3>
          <Link prefetch={false} className="title-link" href={"/anime/" + anime.id}>{anime.title}</Link>
        </h3>
        <p className="card-description" title={originalTitle || undefined}>
          {originalTitle || anime.category}
        </p>
        <div className="card-bottom">
          <span className="episode-count">{anime.isDemo ? "演示资料" : "Bangumi 资料"}</span>
          <FavoriteButton animeId={anime.id} title={anime.title} onToggleSuccess={onToggleSuccess} />
        </div>
      </div>
    </article>
  );
}
