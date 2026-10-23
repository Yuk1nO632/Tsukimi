import { bangumiCatalog, catalogMeta } from "./catalog.generated";

export { catalogMeta };
export const animeList = bangumiCatalog;
export const featuredAnime = catalogMeta.featuredIds
  .map((id) => animeList.find((anime) => anime.id === id))
  .filter(Boolean);

export function getAnime(id) {
  return animeList.find((anime) => anime.id === id);
}

export function getAllAnimeIds() {
  return animeList.map((anime) => anime.id);
}
