"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { requestJson } from "../lib/api";
import useApi from "../lib/use-api";
import { airingSummary, episodeSchedule } from "../lib/airing";
import { useAccount } from "./account-provider";
import { progressUrl } from "./continue-watching";
import { LoadFailure } from "./portal-state";

const EPISODES_PER_PAGE = 50;

function positionText(seconds) {
  const whole = Math.floor(seconds);
  const minutes = Math.floor(whole / 60);
  return `${String(minutes).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

function episodeState(record) {
  if (!record) return "未记录";
  if (record.completed) {
    return record.position > 0 ? "已看完 · 重看到 " + positionText(record.position) : "已看完";
  }
  return `看到 ${positionText(record.position)}`;
}

function HistoryRows({ anime }) {
  const [result, setResult] = useState({ data: null, error: "" });
  const [attempt, setAttempt] = useState(0);
  const [page, setPage] = useState(0);
  useEffect(() => {
    let controller;
    async function read() {
      controller?.abort();
      const request = new AbortController();
      controller = request;
      try {
        const data = await requestJson(
          `/api/progress/${encodeURIComponent(anime.id)}/episodes`,
          { signal: request.signal },
        );
        if (!request.signal.aborted) setResult({ data, error: "" });
      } catch (failure) {
        if (!request.signal.aborted) setResult({ data: null, error: failure.message });
      }
    }
    void read();
    const refresh = () => {
      if (!document.hidden) void read();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("tsukimi-progress-refresh", refresh);
    return () => {
      controller?.abort();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("tsukimi-progress-refresh", refresh);
    };
  }, [anime.id, attempt]);

  if (result.error) {
    return <LoadFailure error={result.error} retry={() => setAttempt((value) => value + 1)} />;
  }
  if (!result.data) return <p role="status">正在读取观看记录…</p>;

  const records = result.data.items;
  const last = result.data.item?.duration > 0 ? result.data.item : null;
  const byEpisode = new Map(records.map((record) => [record.episode, record]));
  const schedule = episodeSchedule(anime, Math.max(last?.episode || 1, records.at(-1)?.episode || 1));
  const scheduledNumbers = new Set(schedule.map(({ number }) => number));
  for (const record of records) {
    if (!scheduledNumbers.has(record.episode)) {
      schedule.push({ number: record.episode, status: "unknown" });
    }
  }
  schedule.sort((a, b) => a.number - b.number);
  const pages = Math.ceil(schedule.length / EPISODES_PER_PAGE);
  const currentPage = Math.min(page, Math.max(0, pages - 1));
  const visible = schedule.slice(currentPage * EPISODES_PER_PAGE, (currentPage + 1) * EPISODES_PER_PAGE);
  const legacy = last && !byEpisode.has(last.episode);

  return (
    <>
      {legacy && (
        <div className="episode-history-legacy">
          <div>
            <p>最近续播 · 第 {last.episode} 集 · {last.completed ? "已看完" : positionText(last.position)}</p>
            <small>逐集记录从功能上线后开始保存。</small>
          </div>
          <Link href={progressUrl(last)} prefetch={false}>
            {last.completed ? "重看这一集" : "继续观看"} →
          </Link>
        </div>
      )}
      <div className="episode-history-summary">
        <p>已记录 {records.length} 集</p>
        {pages > 1 && (
          <select
            aria-label="集数范围"
            value={currentPage}
            onChange={(event) => setPage(Number(event.target.value))}
          >
            {Array.from({ length: pages }, (_, index) => (
              <option key={index} value={index}>
                第 {schedule[index * EPISODES_PER_PAGE].number}–{
                  schedule[Math.min(schedule.length, (index + 1) * EPISODES_PER_PAGE) - 1].number
                } 集
              </option>
            ))}
          </select>
        )}
      </div>
      <ul className="episode-history-list">
        {visible.map((episode) => {
          const record = byEpisode.get(episode.number);
          const state = episodeState(record);
          const title = `第 ${episode.number} 集`;
          const action = record?.position > 0 ? "继续" : record?.completed ? "重看" : "播放";
          return (
            <li key={episode.number} className={record ? "has-record" : ""}>
              {record || episode.status !== "upcoming" ? (
                <Link
                  href={record ? progressUrl(record) : `/watch/${anime.id}?episode=${episode.number}`}
                  prefetch={false}
                  aria-label={`${title}，${state}，${action}`}
                >
                  <strong>{title}</strong>
                  <span>{state}</span>
                  <small>{action} →</small>
                </Link>
              ) : (
                <div>
                  <strong>{title}</strong>
                  <span>{state}</span>
                  <small>未播出</small>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}

export default function EpisodeHistory({ anime: initialAnime }) {
  const account = useAccount();
  const { data } = useApi(`/api/catalog/${encodeURIComponent(initialAnime.id)}`);
  const anime = data || initialAnime;
  return (
    <div className="content-shell portal-page episode-history">
      <nav className="breadcrumbs" aria-label="当前位置">
        <Link href="/account#watch-history" prefetch={false}>观看历史</Link>
        <span>›</span>
        <strong>{anime.title}</strong>
      </nav>
      <header className="episode-history-header">
        <span className="episode-history-cover">
          <Image src={anime.cover} alt="" fill sizes="64px" />
        </span>
        <div>
          <h1>逐集观看历史</h1>
          <p>{anime.title} · {airingSummary(anime)}</p>
        </div>
        <Link className="outline-button" href={`/anime/${anime.id}`} prefetch={false}>番剧详情 →</Link>
      </header>
      {account.ready ? <HistoryRows key={`${account.scope}:${anime.id}`} anime={anime} /> :
        account.error ? <LoadFailure error={account.error} retry={account.reload} /> :
        <p role="status">正在读取观看记录…</p>}
    </div>
  );
}
