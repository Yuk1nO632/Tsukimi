"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { requestJson } from "../lib/api";
import { useAccount } from "./account-provider";

export function progressUrl(item) {
  const query = new URLSearchParams({
    episode: String(item.episode),
    provider: item.source_provider || "anich",
  });
  if (item.source_id) query.set("source", String(item.source_id));
  if (item.line_id) query.set("line", String(item.line_id));
  return `/watch/${item.anime_id || item.anime.id}?${query}`;
}

export default function ContinueWatching({ animeId, manage = false, history = false }) {
  const account = useAccount();
  const pathname = usePathname();
  const [records, setRecords] = useState({ scope: null, items: [] });
  const [expanded, setExpanded] = useState(history);
  const [removing, setRemoving] = useState(null);
  const [removeError, setRemoveError] = useState("");
  const readVersion = useRef(0);
  const activeScope = useRef(account.scope);
  activeScope.current = account.scope;
  const items = records.scope === account.scope ? records.items : [];
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  useEffect(() => {
    if (!account.ready) return;
    const controller = new AbortController();
    async function read() {
      const version = ++readVersion.current;
      try {
        const data = await requestJson(
          animeId
            ? `/api/progress/${encodeURIComponent(animeId)}`
            : "/api/progress",
          {
            signal: controller.signal,
          },
        );
        if (controller.signal.aborted || version !== readVersion.current) return;
        setRecords({
          scope: account.scope,
          items: data.items || (data.item ? [data.item] : []),
        });
        setError("");
      } catch (failure) {
        if (!controller.signal.aborted && version === readVersion.current)
          setError(failure.message);
      }
    }
    setRemoveError("");
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
  useEffect(() => {
    if (!manage) return;
    const expandHistory = () => {
      if (["#continue-watching", "#watch-history"].includes(window.location.hash)) setExpanded(true);
    };
    expandHistory();
    window.addEventListener("hashchange", expandHistory);
    return () => window.removeEventListener("hashchange", expandHistory);
  }, [manage, pathname]);
  async function remove(item) {
    if (
      removing ||
      !window.confirm(`删除《${item.anime.title}》的观看记录？下次播放将从头开始。`)
    )
      return;
    const scope = account.scope;
    setRemoving(item.anime_id);
    setRemoveError("");
    try {
      await requestJson(`/api/progress/${encodeURIComponent(item.anime_id)}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json", "X-Tsukimi-Scope": scope },
        body: JSON.stringify({
          revision: item.revision,
          operation_id: crypto.randomUUID(),
          scope,
        }),
      });
      if (activeScope.current !== scope) return;
      ++readVersion.current;
      setRecords((previous) => ({
        ...previous,
        items: previous.items.filter((record) => record.anime_id !== item.anime_id),
      }));
      try {
        sessionStorage.removeItem(`tsukimi:progress:${scope}:${item.anime_id}`);
      } catch {}
      window.dispatchEvent(new Event("tsukimi-progress-refresh"));
    } catch (failure) {
      if (activeScope.current === scope) {
        setRemoveError(failure.message);
        if (failure.status === 409)
          window.dispatchEvent(new Event("tsukimi-progress-refresh"));
      }
    } finally {
      setRemoving(null);
    }
  }
  const available = items.filter(
    (item) =>
      (history || (!item.completed && item.position > 0)) &&
      item.duration > 0 &&
      (!animeId || (item.anime?.id || item.anime_id) === animeId),
  );
  const visible = available.slice(
    0,
    animeId ? 1 : manage && expanded ? available.length : 6,
  );
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
  if (!visible.length) return history ? (
    <section id="watch-history" className="continue-section" aria-label="观看历史">
      <div className="portal-section-heading"><h2>观看历史</h2></div>
      <p className="history-empty" role="status">
        {!account.ready || records.scope !== account.scope ? "正在读取观看记录…" : "还没有观看记录，播放番剧后会自动保存。"}
      </p>
    </section>
  ) : null;
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
    <section id={history ? "watch-history" : "continue-watching"} className="continue-section" aria-label={history ? "观看历史" : "继续观看"}>
      <div className="portal-section-heading">
        <div>
          <h2>{history ? `观看历史（${available.length}）` : "继续观看"}</h2>
          <span>
            {account.user ? "已同步的观看记录" : "当前浏览器的观看记录"}
          </span>
        </div>
        {manage && available.length > 6 && (
          <button
            className="text-button"
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "收起记录" : `查看全部（${available.length}）`}
          </button>
        )}
        {!manage && (
          <Link href="/account#watch-history">
            观看历史 →
          </Link>
        )}
      </div>
      {removeError && (
        <p className="progress-read-error" role="alert">{removeError}</p>
      )}
      <div className="continue-grid">
        {visible.map((item) => (
          <article className="continue-card" key={item.anime.id}>
            <Link
              prefetch={false}
              className="continue-card-link"
              href={progressUrl(item)}
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
                <small>{item.completed ? "已看完 · 再次播放 →" : "继续播放 →"}</small>
              </span>
            </Link>
            <button
              className="continue-remove"
              type="button"
              aria-label={`删除《${item.anime.title}》的观看记录`}
              disabled={removing !== null || account.busy}
              onClick={() => void remove(item)}
            >
              {removing === item.anime_id ? "删除中…" : "删除记录"}
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
