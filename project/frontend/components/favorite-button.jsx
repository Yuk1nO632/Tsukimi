"use client";

import { useCollection } from "./collection-provider";

export default function FavoriteButton({ animeId, title, onToggleSuccess }) {
  const { favoriteIds, toggleFavorite, status, pendingId } = useCollection();
  const isFavorite = favoriteIds.includes(animeId);
  const isPending = pendingId === animeId;

  return (
    <button
      className="favorite-button"
      type="button"
      aria-pressed={isFavorite}
      aria-busy={isPending}
      aria-label={`${isPending ? "正在保存" : isFavorite ? "取消收藏" : "收藏"}《${title}》`}
      disabled={status !== "ready" || pendingId !== null}
      onClick={async () => {
        const saved = await toggleFavorite(animeId);
        if (saved) onToggleSuccess?.(isFavorite);
      }}
    >
      <span className="favorite-icon" aria-hidden="true">{isFavorite ? "♥" : "♡"}</span>
      <span>{isPending ? "保存中…" : isFavorite ? "已收藏" : "收藏"}</span>
    </button>
  );
}
