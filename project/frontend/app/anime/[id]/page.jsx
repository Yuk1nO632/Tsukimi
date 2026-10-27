import { notFound } from "next/navigation";
import { loadAnime } from "../../../lib/anime-server";
import bindings from "../../../../catalog/xifan-bindings.json";
import DetailView from "../../../components/detail-view";
export const dynamic = "force-dynamic";
export async function generateMetadata({ params }) {
  const { id } = await params;
  const anime = await loadAnime(id);
  return { title: anime?.title || "未找到番剧" };
}
export default async function AnimeDetailPage({ params, searchParams }) {
  const { id } = await params;
  const anime = await loadAnime(id);
  if (!anime) notFound();
  const query = await searchParams;
  const selected =
    typeof query.source === "string" &&
    /^[1-9]\d*$/.test(query.source) &&
    Number.isSafeInteger(Number(query.source))
      ? Number(query.source)
      : bindings[id] || null;
  return <DetailView key={id} anime={anime} initialSource={selected} />;
}
