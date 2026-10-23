import { bangumiCatalog, catalogMeta } from "./catalog.generated";
export { catalogMeta };
export const animeList = bangumiCatalog;
// 当前为虚构演示资料。后续由 FastAPI 接口提供真实番剧资料。
const legacyDemoList = [
  {
    id: "forest", title: "月光邮便局", category: "奇幻 / 日常", episodes: 12,
    description: "把没来得及说的话，寄给月亮另一端的人。",
    synopsis: "森林深处，有一间只在月圆时营业的邮便局。新来的见习邮差带着一封没有地址的信，开始走访那些等待回音的人。每一次投递，都是一个关于相遇、告别与重新出发的小故事。",
    scene: "forest", lettering: "Letters\nto the Moon", kicker: "A STORY IN THE FOREST",
    season: "秋日故事", status: "演示条目", duration: "约 24 分钟 / 集",
  },
  {
    id: "coast", title: "海风经过的夏天", category: "青春 / 治愈", episodes: 12,
    description: "小镇、海风，还有一个不想结束的夏天。",
    synopsis: "在最后一个暑假，一群年轻人决定修复海边废弃的观景站。潮汐带来新的朋友，也带走不愿说出口的心事。随着夏日渐渐结束，他们学会把约定留给未来，把今天留给彼此。",
    scene: "coast", lettering: "Where the\nSea Whispers", kicker: "A SUMMER TO REMEMBER",
    season: "夏日故事", status: "演示条目", duration: "约 24 分钟 / 集",
  },
  {
    id: "evening", title: "黄昏的慢行列车", category: "旅行 / 日常", episodes: 10,
    description: "下一站没有目的地，只有沿途遇见的故事。",
    synopsis: "一张没有终点的车票，把旅人带上穿过山川与小镇的慢行列车。每个傍晚，列车都会停在一个不同的地方。旅人收集沿途的声音与故事，逐渐找到属于自己的前进方向。",
    scene: "evening", lettering: "One More\nStop", kicker: "TAKE THE SLOW WAY HOME",
    season: "旅途故事", status: "演示条目", duration: "约 25 分钟 / 集",
  },
];


// 兼容之前的学习示例链接，首页正式片单只展示真实资料。
const demoArtwork = { forest: "/artwork/moonlight.png", coast: "/artwork/seabreeze.png", evening: "/artwork/sunset-train.png" };
const legacyAnime = legacyDemoList.map((anime) => ({ ...anime, cover: demoArtwork[anime.id], isDemo: true, tags: anime.category.split(" / "), score: 0 }));
export function getAnime(id) {
  return animeList.find((anime) => anime.id === id) || legacyAnime.find((anime) => anime.id === id);
}
export function getAllAnimeIds() {
  return [...animeList, ...legacyAnime].map((anime) => anime.id);
}
