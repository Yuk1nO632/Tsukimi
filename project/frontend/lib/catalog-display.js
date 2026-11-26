const seasons = ["冬季", "春季", "夏季", "秋季"];

export function releaseLabel(anime) {
  const date = /^(\d{4})-(0?[1-9]|1[0-2])(?:-|$)/.exec(anime.releaseDate || "");
  if (date) return date[1] + " 年" + seasons[Math.ceil(Number(date[2]) / 3) - 1];
  return anime.year ? anime.year + " 年" : "首播时间待定";
}

export function platformLabel(platform) {
  return /^movie$/i.test(platform || "") ? "剧场版" : platform || "动画";
}

export function searchPartLabel(anime) {
  const part = /第\s*[零〇一二三四五六七八九十百\d]+\s*[季期部篇]|(?:season|part|cour)[\s.]+(?:\d+|[ivx]+)\b/i;
  const arc = /[·・:：]\s*([^·・:：/\r\n]{1,32}[篇編])$/;
  for (const title of [anime.title, anime.originalTitle, anime.aliases]) {
    if (!title) continue;
    const key = title.normalize("NFKC").trim();
    const label = key.match(part)?.[0] || key.match(arc)?.[1];
    if (label) return label;
  }
  return "";
}
