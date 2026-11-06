"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { requestJson } from "../lib/api";
import { useAccount } from "./account-provider";

export function progressUrl(item) {
  const query = new URLSearchParams({
    episode: String(item.episode),
    provider: "anich",
  });
  if (item.source_id) query.set("source", String(item.source_id));
  if (item.line_id) query.set("line", String(item.line_id));
  return `/watch/${item.anime_id || item.anime.id}?${query}`;
}

export default function ContinueWatching({ animeId }) {
  const account = useAccount();
  const pathname = usePathname();
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    if (!account.ready) return;
    const controller = new AbortController();
    let readVersion = 0;
    async function read() {
      const version = ++readVersion;
      try {
        const data = await requestJson(
          animeId
            ? `/api/progress/${encodeURIComponent(animeId)}`
            : "/api/progress",
          {
            signal: controller.signal,
          },
        );
        if (controller.signal.aborted || version !== readVersion) return;
        setItems(data.items || (data.item ? [data.item] : []));
        setError("");
      } catch (failure) {
        if (!controller.signal.aborted && version === readVersion)
          setError(failure.message);
      }
    }
    void read();
    const refresh = () => {
      if (document.visibilityState === "visible") void read();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("tsukimi-library-refresh", refresh);
    window.addEventListener("tsukimi-progress-refresh", refresh);
    return () => {
      controller.abort();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("tsukimi-library-refresh", refresh);
      window.removeEventListener("tsukimi-progress-refresh", refresh);
    };
  }, [account.scope, account.ready, pathname, version, animeId]);
  const visible = items
    .filter(
      (item) =>
        !item.completed &&
        item.position > 0 &&
        (!animeId || (item.anime?.id || item.anime_id) === animeId),
    )
    .slice(0, animeId ? 1 : 6);
  if (error)
    return (
      <p className="progress-read-error" role="status">
        观看记录暂时无法读取。
        <button
          className="text-button"
          onClick={() => setVersion((value) => value + 1)}
        >
          重试
        </button>
      </p>
    );
  if (!visible.length) return null;
  if (animeId)
    return (
      <Link
        className="outline-button resume-detail"
        href={progressUrl(visible[0])}
        prefetch={false}
      >
        继续第 {visible[0].episode} 集 · {Math.floor(visible[0].position / 60)}{" "}
        分 {Math.floor(visible[0].position % 60)} 秒 →
      </Link>
    );
  return (
    <section className="continue-section" aria-label="继续观看">
      <div className="portal-section-heading">
        <div>
          <h2>继续观看</h2>
          <span>
            {account.user ? "已同步的观看记录" : "当前浏览器的观看记录"}
          </span>
        </div>
        <Link href="/collection">我的追番 →</Link>
      </div>
      <div className="continue-grid">
        {visible.map((item) => (
          <Link
            prefetch={false}
            className="continue-card"
            href={progressUrl(item)}
            key={item.anime.id}
          >
            <span className="continue-cover">
              <Image src={item.anime.cover} alt="" fill sizes="72px" />
            </span>
            <span className="continue-copy">
              <strong>{item.anime.title}</strong>
              <span>
                第 {item.episode} 集 · {Math.floor(item.position / 60)} 分{" "}
                {Math.floor(item.position % 60)} 秒
              </span>
              <span className="continue-track">
                <i
                  style={{
                    width: `${Math.min(100, (item.position / item.duration) * 100)}%`,
                  }}
                />
              </span>
              <small>继续播放 →</small>
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}
