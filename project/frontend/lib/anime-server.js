import { cache } from "react";
import { getAnime } from "./anime";

// Render from the backend snapshot first. DetailView enriches after the page is usable.
// React cache deduplicates metadata/page reads within the same render.
export const loadAnime = cache(async (id) => {
  if (!/^bgm-[1-9]\d{0,8}$/.test(id)) return null;
  try {
    const response = await fetch(
      `${process.env.TSUKIMI_API_ORIGIN || "http://127.0.0.1:8000"}/api/catalog/${id}?summary=true`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(20000),
      },
    );
    if (response.status === 404) return null;
    if (!response.ok) throw new Error("番剧资料暂时不可用");
    return await response.json();
  } catch {
    const fallback = getAnime(id);
    if (fallback)
      return {
        ...fallback,
        detailWarning: "资料服务暂不可用，当前展示本地缓存。",
      };
    throw new Error("番剧资料暂时无法读取，请重试。");
  }
});
