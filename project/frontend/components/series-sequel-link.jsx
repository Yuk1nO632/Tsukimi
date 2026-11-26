"use client";

import Link from "next/link";
import useApi from "../lib/use-api";
import PlayerIcon from "./player-icon";

export default function SeriesSequelLink({ animeId }) {
  const { data } = useApi("/api/catalog/" + animeId + "/series");
  const sequel = data?.sequel;
  if (!sequel) return null;
  return (
    <Link href={"/anime/" + sequel.id} prefetch={false} title={sequel.title}>
      查看续作 <PlayerIcon name="next" size={16} />
    </Link>
  );
}
