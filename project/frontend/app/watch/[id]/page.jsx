import { notFound } from "next/navigation";
import { getAllAnimeIds, getAnime } from "../../../lib/anime";
import WatchStudio from "../../../components/watch-studio";
export const dynamicParams = false;
export function generateStaticParams() { return getAllAnimeIds().map((id) => ({ id })); }
export async function generateMetadata({ params }) {
  const { id } = await params;
  return { title: `${getAnime(id)?.title || "未找到番剧"} · 放映室` };
}
export default async function WatchPage({ params, searchParams }) {
  const { id } = await params;
  const query = await searchParams;
  const anime = getAnime(id);
  if (!anime) notFound();
  const value = query.episode ?? "1";
  if (typeof value !== "string" || !/^[1-9]\d*$/.test(value)) notFound();
  const selectedEpisode = Number(value);
  if (!Number.isSafeInteger(selectedEpisode) || selectedEpisode > anime.episodes) notFound();
  function optionalId(value) {
    if (value === undefined) return null;
    if (typeof value !== "string" || !/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) notFound();
    return Number(value);
  }
  const selectedSourceId = optionalId(query.source);
  const selectedLineId = optionalId(query.line);
  return <WatchStudio key={`${id}:${selectedEpisode}:${selectedSourceId}:${selectedLineId}`} anime={anime} selectedEpisode={selectedEpisode} selectedSourceId={selectedSourceId} selectedLineId={selectedLineId} />;
}
