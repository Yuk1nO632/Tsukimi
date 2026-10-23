// 同一个组件负责每张卡片的结构，具体显示什么由 App 传入的 props 决定。
export default function AnimeCard({ anime, number, isFavorite, onToggle }) {
  return (
    <article className="anime-card">
      <div className={`poster scene-${anime.scene}`} aria-hidden="true">
        <span className="poster-grain" />
        <span className="poster-disc" />
        <span className="poster-hill hill-back" />
        <span className="poster-hill hill-front" />
        <span className="poster-line" />
        <span className="poster-kicker">{anime.kicker}</span>
        <span className="poster-lettering">{anime.lettering}</span>
        <span className="poster-number">{String(number).padStart(2, "0")}</span>
      </div>
      <div className="card-body">
        <p className="card-meta">{anime.category}</p>
        <h3>{anime.title}</h3>
        <p className="card-description">{anime.description}</p>
        <div className="card-bottom">
          <span className="episode-count">全 {anime.episodes} 集 · 演示条目</span>
          <button
            className="favorite-button"
            type="button"
            aria-pressed={isFavorite}
            aria-label={`${isFavorite ? "取消收藏" : "收藏"}《${anime.title}》`}
            onClick={() => onToggle(anime.id)}
          >
            <span className="favorite-icon" aria-hidden="true">{isFavorite ? "♥" : "♡"}</span>
            <span className="favorite-label">{isFavorite ? "已收藏" : "收藏"}</span>
          </button>
        </div>
      </div>
    </article>
  );
}
