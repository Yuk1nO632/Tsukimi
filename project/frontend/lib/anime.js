import catalog from "../../catalog/catalog.json";

export const catalogMeta = catalog.meta;
export const animeList = catalog.anime;
export const featuredAnime = catalogMeta.featuredIds
  .map((id) => animeList.find((anime) => anime.id === id))
  .filter(Boolean);

export function getAnime(id) {
  return animeList.find((anime) => anime.id === id);
}

export function getAllAnimeIds() {
  return animeList.map((anime) => anime.id);
}
