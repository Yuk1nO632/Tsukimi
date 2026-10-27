"use client";
import { useState } from "react";
import Image from "next/image";
export default function AnimePoster({ anime }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`poster${anime.isDemo ? " is-demo-poster" : ""}`}>
      <Image src={failed ? "/covers/placeholder.svg" : anime.cover} onError={() => setFailed(true)} alt="" fill sizes="(max-width: 600px) 45vw, (max-width: 1000px) 25vw, 220px" />
      <span className="poster-gradient" />
      <span className="poster-episodes">{anime.episodes > 0 ? `全 ${anime.episodes} 集` : "集数待定"}</span>
      {anime.score > 0 && <span className="poster-score">{anime.score.toFixed(1)}</span>}
      {anime.isDemo && <span className="poster-demo">演示</span>}
    </div>
  );
}
