"use client";

import { useCollection } from "./collection-provider";

export default function FavoriteButton({ animeId, title, onBeforeToggle }) {
  const { favoriteIds, toggleFavorite } = useCollection();
  const isFavorite = favoriteIds.includes(animeId);

  return (
    <button
      className="favorite-button"
      type="button"
      aria-pressed={isFavorite}
      aria-label={`${isFavorite ? "取消收藏" : "收藏"}《${title}》`}
      onClick={() => {
        onBeforeToggle?.(isFavorite);
        toggleFavorite(animeId);
      }}
    >
      <span className="favorite-icon" aria-hidden="true">{isFavorite ? "♥" : "♡"}</span>
      <span>{isFavorite ? "已收藏" : "收藏"}</span>
    </button>
  );
}
