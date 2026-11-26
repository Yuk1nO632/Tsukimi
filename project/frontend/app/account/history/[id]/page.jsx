import { notFound } from "next/navigation";
import EpisodeHistory from "../../../../components/episode-history";
import { loadAnime } from "../../../../lib/anime-server";

export const dynamic = "force-dynamic";

export const metadata = { title: "逐集观看历史" };

export default async function EpisodeHistoryPage({ params }) {
  const { id } = await params;
  const anime = await loadAnime(id);
  if (!anime) notFound();
  return <EpisodeHistory anime={anime} />;
}
