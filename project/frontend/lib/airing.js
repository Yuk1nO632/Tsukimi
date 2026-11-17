export function airingSummary(anime) {
  const airing = anime.airing;
  const total = anime.episodes > 0 ? `共 ${anime.episodes} 集` : "总集数待定";
  if (airing?.status === "completed") return `已完结 · ${total}`;
  if (airing?.status === "upcoming") return `未开播 · ${total}`;
  if (airing?.airedCount > 0) {
    const progress =
      airing.airedCount === airing.latestEpisode
        ? `更新至第 ${airing.latestEpisode} 集`
        : `已播 ${airing.airedCount} 集 · 最新第 ${airing.latestEpisode} 集`;
    const status = airing.status === "airing" ? "连载中" : "完结状态待确认";
    return `${status} · ${progress} · ${total}`;
  }
  return `更新进度待确认 · ${total}`;
}

export function episodeSchedule(anime, fallbackCount = 1) {
  const entries = new Map(
    (anime.airing?.episodes || []).map((episode) => [episode.number, episode]),
  );
  const count = Math.min(
    10000,
    anime.episodes || Math.max(fallbackCount, ...entries.keys()),
  );
  return Array.from(
    { length: count },
    (_, index) =>
      entries.get(index + 1) || {
        number: index + 1,
        status: anime.airing?.status === "upcoming" ? "upcoming" : "unknown",
        airdate: "",
      },
  );
}
