async function request(path, signal) {
  const timeout = AbortSignal.timeout(30000);
  const response = await fetch(path, { cache: "no-store", signal: signal ? AbortSignal.any([signal, timeout]) : timeout });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof data?.detail === "string" ? data.detail : "暂时无法读取视频来源，请重试。");
  if (!data || typeof data !== "object") throw new Error("来源返回了无法识别的资料。");
  return data;
}

export function readPlayback(animeId, episode, sourceAnimeId, lineId, signal) {
  const query = new URLSearchParams({ episode: String(episode) });
  if (sourceAnimeId) query.set("source_anime_id", String(sourceAnimeId));
  if (lineId) query.set("line_id", String(lineId));
  return request(`/api/playback/${encodeURIComponent(animeId)}?${query}`, signal);
}

export function searchXifan(query, signal) {
  return request(`/api/sources/xifan/search?q=${encodeURIComponent(query)}`, signal);
}
