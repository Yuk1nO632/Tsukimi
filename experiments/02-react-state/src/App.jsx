import { useRef, useState } from "react";
import AnimeCard from "./components/AnimeCard.jsx";
import { animeList } from "./data.js";

export default function App() {
  // 1. state：React 为这个组件记住的数据，仍然位于浏览器页面内存中。
  const [favoriteIds, setFavoriteIds] = useState([]);
  const [currentFilter, setCurrentFilter] = useState("all");
  const [feedback, setFeedback] = useState("试着收藏一个故事吧。");

  // 这两个 ref 只辅助键盘焦点：移除卡片后，仍能继续操作筛选。
  // 它们不是收藏数据；本课先关注 useState，useRef 可暂时略过。
  const allFilterRef = useRef(null);
  const favoritesFilterRef = useRef(null);

  // 2. 从 state 算出显示结果，不再另外维护一份容易不同步的计数。
  const favoriteCount = favoriteIds.length;
  const visibleAnime = animeList.filter(
    (anime) => currentFilter === "all" || favoriteIds.includes(anime.id),
  );

  // 3. 事件处理只更新 state；界面由 React 根据新数据更新。
  function toggleFavorite(animeId) {
    const anime = animeList.find((item) => item.id === animeId);
    if (!anime) return;
    const wasFavorite = favoriteIds.includes(animeId);

    if (wasFavorite && currentFilter === "favorites") {
      favoritesFilterRef.current?.focus({ preventScroll: true });
    }
    setFavoriteIds((previousIds) =>
      previousIds.includes(animeId)
        ? previousIds.filter((id) => id !== animeId)
        : [...previousIds, animeId],
    );
    setFeedback(wasFavorite ? `已取消收藏《${anime.title}》。` : `已收藏《${anime.title}》。`);
  }

  function changeFilter(filter) {
    setCurrentFilter(filter);
    setFeedback(filter === "all" ? "正在显示全部演示条目。" : `当前收藏了 ${favoriteCount} 个故事。`);
  }

  function showAll() {
    changeFilter("all");
    allFilterRef.current?.focus({ preventScroll: true });
  }

  // 4. JSX 描述“当前数据下，页面应该是什么样”。
  return (
    <div className="page-shell">
      <header className="site-header">
        <a className="brand" href="./" aria-label="Tsukimi 首页">
          <span className="brand-mark" aria-hidden="true" />Tsukimi<span className="brand-caption">月见</span>
        </a>
        <span className="header-note">一份属于自己的追番单</span>
        <div className="saved-indicator">
          <span aria-hidden="true">♡</span><span>已收藏 <strong id="header-count">{favoriteCount}</strong></span>
        </div>
      </header>

      <main>
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <span className="eyebrow">A LITTLE TIME FOR YOUR STORIES</span>
            <h1 id="hero-title">月下片刻，<br />故事未完<span className="accent-dot">。</span></h1>
            <p>把喜欢的故事留在这里。<br />从一份小小的追番单，开始下一集的期待。</p>
            <span className="hero-label"><span className="status-dot" aria-hidden="true" />Tsukimi · 最初的一页</span>
          </div>
          <div className="moon-scene" aria-hidden="true">
            <span className="moon-orbit orbit-one" /><span className="moon-orbit orbit-two" />
            <span className="large-moon" /><span className="small-star star-one">✦</span>
            <span className="small-star star-two">✧</span><span className="scene-caption">月がきれいですね</span>
          </div>
        </section>

        <section className="library" aria-labelledby="library-title">
          <div className="section-heading">
            <div>
              <span className="eyebrow">YOUR LITTLE COLLECTION</span>
              <h2 id="library-title">我的追番单 <span className="library-total">{String(animeList.length).padStart(2, "0")}</span></h2>
            </div>
            <div className="filters" role="group" aria-label="番剧筛选">
              <button ref={allFilterRef} type="button" className={`filter-button${currentFilter === "all" ? " is-active" : ""}`} aria-pressed={currentFilter === "all"} onClick={() => changeFilter("all")}>全部</button>
              <button ref={favoritesFilterRef} type="button" className={`filter-button${currentFilter === "favorites" ? " is-active" : ""}`} aria-pressed={currentFilter === "favorites"} onClick={() => changeFilter("favorites")}>已收藏 <span id="filter-count">{favoriteCount}</span></button>
            </div>
          </div>

          <div className="anime-grid" hidden={visibleAnime.length === 0}>
            {/* 5. 复用卡片组件，资料、状态、操作通过 props 传进去。 */}
            {visibleAnime.map((anime) => (
              <AnimeCard
                key={anime.id}
                anime={anime}
                number={animeList.findIndex((item) => item.id === anime.id) + 1}
                isFavorite={favoriteIds.includes(anime.id)}
                onToggle={toggleFavorite}
              />
            ))}
          </div>

          {visibleAnime.length === 0 && (
            <div className="empty-state">
              <span aria-hidden="true">☾</span><h3>这里还没有收藏</h3>
              <p>遇见喜欢的故事，就为它留一个位置。</p>
              <button type="button" onClick={showAll}>浏览全部</button>
            </div>
          )}
          <p className="feedback" role="status" aria-live="polite">{feedback}</p>
        </section>

        <aside className="experiment-note" aria-label="实验说明">
          <span className="note-label">实验 02</span>
          <p>React 管理组件与状态。这里使用虚构演示条目，收藏仍会在刷新后重置。</p>
          <span className="note-detail">组件 · props · state</span>
        </aside>
      </main>
      <footer>
        <span>Tsukimi <span className="footer-dot">·</span> 下一集，继续喜欢。</span>
        <span>MADE FOR THE STORIES YOU LOVE</span>
      </footer>
    </div>
  );
}
