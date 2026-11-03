// Popular works with enough ratings; this is a selection, not a global ranking.
export function selectPopularPicks(items, limit = 6) {
  if (!Array.isArray(items)) return [];
  return items
    .filter(
      (item) =>
        Number.isFinite(item?.score) &&
        item.score >= 8 &&
        item.ratingCount >= 1000,
    )
    .sort((a, b) => b.score - a.score || b.ratingCount - a.ratingCount)
    .slice(0, limit);
}
