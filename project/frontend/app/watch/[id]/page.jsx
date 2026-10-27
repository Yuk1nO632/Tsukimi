import { notFound } from "next/navigation";
import { loadAnime } from "../../../lib/anime-server";
import WatchStudio from "../../../components/watch-studio";
export const dynamic = "force-dynamic";

export async function generateMetadata({ params }) {
  const { id } = await params;
  return { title: `${(await loadAnime(id))?.title || "未找到番剧"} · 放映室` };
}
export default async function WatchPage({ params, searchParams }) {
  const { id } = await params;
  const query = await searchParams;
  const anime = await loadAnime(id);
  if (!anime) notFound();
  const value = query.episode ?? "1";
  if (typeof value !== "string" || !/^[1-9]\d*$/.test(value)) notFound();
  const selectedEpisode = Number(value);
  if (
    !Number.isSafeInteger(selectedEpisode) ||
    (anime.episodes > 0 && selectedEpisode > anime.episodes)
  )
    notFound();
  function optionalId(value) {
    if (value === undefined) return null;
    if (
      typeof value !== "string" ||
      !/^[1-9]\d*$/.test(value) ||
      !Number.isSafeInteger(Number(value))
    )
      notFound();
    return Number(value);
  }
  const selectedSourceId = optionalId(query.source);
  const selectedLineId = optionalId(query.line);
  return (
    <WatchStudio
      key={`${id}:${selectedEpisode}:${selectedSourceId}:${selectedLineId}`}
      anime={anime}
      selectedEpisode={selectedEpisode}
      selectedSourceId={selectedSourceId}
      selectedLineId={selectedLineId}
    />
  );
}
