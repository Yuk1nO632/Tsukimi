export function readCatalogParams(params) {
  const single = (key) => (typeof params[key] === "string" ? params[key] : "");
  const q = single("q").trim().slice(0, 100);
  const year =
    /^\d{4}$/.test(single("year")) &&
    Number(single("year")) >= 1900 &&
    Number(single("year")) <= 2100
      ? single("year")
      : "";
  const season = /^[1-4]$/.test(single("season")) ? single("season") : "";
  const genre = single("genre").slice(0, 20);
  const sort = ["match", "heat", "score", "rank"].includes(single("sort"))
    ? single("sort")
    : q
      ? "match"
      : "heat";
  const page =
    /^[1-9]\d*$/.test(single("page")) && Number(single("page")) <= 200
      ? single("page")
      : "1";
  return { q, year, season, genre, sort, page };
}
export const genres = [
  "奇幻",
  "科幻",
  "日常",
  "恋爱",
  "悬疑",
  "治愈",
  "音乐",
  "战斗",
  "搞笑",
  "运动",
  "冒险",
];
export function currentSeason() {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Shanghai",
      year: "numeric",
      month: "numeric",
    })
      .formatToParts(new Date())
      .map((part) => [part.type, part.value]),
  );
  return {
    year: Number(parts.year),
    season: Math.ceil(Number(parts.month) / 3),
  };
}
