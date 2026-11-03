import Image from "next/image";
import Link from "next/link";

export default function HomeSeasonRanking({
  items = [],
  loading,
  error,
  retry,
  seasonUrl,
}) {
  return (
    <aside className="home-season-ranking" aria-labelledby="home-ranking-title">
      <div className="ranking-heading">
        <div>
          <h2 id="home-ranking-title">本季人气榜</h2>
        </div>
        <Link
          prefetch={false}
          href={seasonUrl}
          aria-label="查看本季人气榜全部番剧"
        >
          全部 ↗
        </Link>
      </div>
      <p className="ranking-caption">按 Bangumi 收藏热度排序</p>
      {loading ? (
        <div
          className="ranking-skeleton"
          role="status"
          aria-label="正在读取本季人气榜"
        >
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index}>
              <span />
              <i />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="ranking-empty">
          <p>本季榜单暂时无法读取</p>
          <button type="button" onClick={retry}>
            重新加载
          </button>
        </div>
      ) : !items.length ? (
        <p className="ranking-empty">暂无本季番剧资料</p>
      ) : (
        <ol className="season-ranking-list" aria-label="本季收藏热度排名">
          {items.slice(0, 5).map((anime, index) => (
            <li key={anime.id}>
              <Link
                prefetch={false}
                href={`/anime/${anime.id}`}
                aria-label={`人气第 ${index + 1}：${anime.title}`}
              >
                <span
                  className={`ranking-number${index < 3 ? " is-leading" : ""}`}
                >
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="ranking-cover">
                  <Image src={anime.cover} alt="" fill sizes="44px" />
                </span>
                <span className="ranking-copy">
                  <strong>{anime.title}</strong>
                  <small>
                    {anime.platform || "动画"} ·{" "}
                    {anime.episodes > 0 ? `${anime.episodes} 集` : "集数待定"}
                  </small>
                </span>
                {anime.score > 0 && (
                  <b
                    className="ranking-score"
                    aria-label={`评分 ${anime.score.toFixed(1)} 分`}
                  >
                    {anime.score.toFixed(1)}
                  </b>
                )}
              </Link>
            </li>
          ))}
        </ol>
      )}
      <div className="ranking-footer">
        <span>资料热度 ≠ 播放量</span>
        <Link prefetch={false} href="/browse?sort=heat">
          更多热门番剧 →
        </Link>
      </div>
    </aside>
  );
}
