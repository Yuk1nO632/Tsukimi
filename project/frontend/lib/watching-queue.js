const DAY = 86400000;
const shanghaiDate = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
});
const airingDate = new Intl.DateTimeFormat("zh-CN", {
  timeZone: "UTC", month: "long", day: "numeric",
});

export function dateInShanghai(value = Date.now()) {
  const parts = shanghaiDate.formatToParts(new Date(value));
  const { year, month, day } = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return [year, month, day].join("-");
}

function dateValue(date) {
  return Date.parse(date + "T00:00:00Z");
}

export function formatAiringDate(date) {
  return airingDate.format(dateValue(date));
}

export function buildWatchingQueue(items, schedules, progress, today = dateInShanghai()) {
  const releases = [];
  const upcoming = [];
  const todayValue = dateValue(today);
  const tomorrow = todayValue + DAY;
  const weekEnd = todayValue + ((7 - new Date(todayValue).getUTCDay()) % 7) * DAY;
  const cutoff = todayValue - 6 * DAY;

  for (const { anime, updated_at: followedAt } of items) {
    const schedule = schedules.get(anime.id);
    if (!schedule?.episodes) continue;
    const watched = progress?.get(anime.id);
    const lastEpisode = Math.max(watched?.episode || 0, watched?.furthest_episode || 0);
    const activity = watched?.updated_at || followedAt * 1000;
    const since = activity > 0 ? Math.min(cutoff, dateValue(dateInShanghai(activity))) : cutoff;
    // Dates describe scheduled releases. Today's entry has no precise airing time.
    const candidates = schedule.episodes.filter(({ number, airdate }) =>
      number > lastEpisode && airdate && Number.isFinite(dateValue(airdate)));
    const aired = candidates.filter(({ status, airdate }) => status === "aired" && airdate <= today);
    const hasNewRelease = Boolean(progress) && aired.some(({ airdate }) => dateValue(airdate) >= since);
    if (hasNewRelease) {
      const next = aired.reduce((first, episode) => episode.number < first.number ? episode : first);
      const latestDate = aired.reduce((latest, { airdate }) => airdate > latest ? airdate : latest, "");
      releases.push({ anime, episode: next, watched, latestDate });
    }

    const future = candidates.filter(({ status, airdate }) => (
      (status === "upcoming" && airdate >= today) ||
      (!hasNewRelease && status === "aired" && airdate === today)
    ));
    const next = future.reduce((earliest, episode) =>
      !earliest || episode.airdate < earliest.airdate ||
      (episode.airdate === earliest.airdate && episode.number < earliest.number) ? episode : earliest, null);
    if (next) upcoming.push({ anime, episode: next, watched });
  }

  releases.sort((a, b) => b.latestDate.localeCompare(a.latestDate) || a.anime.title.localeCompare(b.anime.title, "zh"));
  upcoming.sort((a, b) => a.episode.airdate.localeCompare(b.episode.airdate) || a.anime.title.localeCompare(b.anime.title, "zh"));
  const groups = new Map([["今天", []], ["明天", []], ["本周", []], ["稍后", []]]);
  for (const item of upcoming) {
    const scheduled = dateValue(item.episode.airdate);
    const group = scheduled === todayValue ? "今天" : scheduled === tomorrow ? "明天" : scheduled <= weekEnd ? "本周" : "稍后";
    groups.get(group).push(item);
  }
  return { releases, upcoming: [...groups].filter(([, rows]) => rows.length) };
}
