// Browser requests stay on the frontend origin; Next.js forwards /api to FastAPI.
async function requestFavorites(method, animeId, signal) {
  const timeout = AbortSignal.timeout(10000);
  const requestSignal = signal ? AbortSignal.any([signal, timeout]) : timeout;
  let response;
  try {
    response = await fetch(animeId ? `/api/favorites/${encodeURIComponent(animeId)}` : "/api/favorites", {
      method, credentials: "same-origin", cache: "no-store", signal: requestSignal,
    });
  } catch {
    throw new Error("暂时无法连接收藏服务，请稍后重新读取收藏确认结果。");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(typeof data?.detail === "string" ? data.detail : "收藏服务暂时不可用，请稍后重试。");
    error.status = response.status;
    throw error;
  }
  if (!Array.isArray(data?.favorite_ids) || !data.favorite_ids.every((id) => typeof id === "string")) {
    throw new Error("收藏资料暂时无法读取，请重试。");
  }
  return data.favorite_ids;
}

export const readFavorites = (signal) => requestFavorites("GET", null, signal);
export const writeFavorite = (animeId, saved) => requestFavorites(saved ? "PUT" : "DELETE", animeId);
