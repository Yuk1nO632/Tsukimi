"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getAnime } from "../lib/anime";

const CollectionContext = createContext(null);

// 放在公共 layout 中：首页与详情共享这份 state，Link 导航时继续保留。
// 本阶段仍是页面内存，完整刷新后重新初始化；下一阶段接 FastAPI 与 SQLite。
export function CollectionProvider({ children }) {
  const [favoriteIds, setFavoriteIds] = useState([]);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(""), 2800);
    return () => clearTimeout(timer);
  }, [feedback]);

  function toggleFavorite(id) {
    const anime = getAnime(id);
    if (!anime) return;
    const wasFavorite = favoriteIds.includes(id);
    setFavoriteIds((previous) => previous.includes(id)
      ? previous.filter((savedId) => savedId !== id)
      : [...previous, id]);
    setFeedback(wasFavorite ? `已取消收藏《${anime.title}》。` : `已收藏《${anime.title}》。`);
  }

  return (
    <CollectionContext.Provider value={{ favoriteIds, toggleFavorite, feedback }}>
      {children}
    </CollectionContext.Provider>
  );
}

export function useCollection() {
  const collection = useContext(CollectionContext);
  if (!collection) throw new Error("useCollection must be used within CollectionProvider");
  return collection;
}

export function CollectionFeedback() {
  const { feedback } = useCollection();
  return <p className="collection-feedback" role="status" aria-live="polite">{feedback}</p>;
}
