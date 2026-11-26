"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { requestJson } from "../lib/api";
import { readPlayback } from "../lib/playback-api";
import { cachedPublic, forgetPublic, readPublic } from "../lib/public-cache";
import { buildWatchingQueue, dateInShanghai, formatAiringDate } from "../lib/watching-queue";

function useSchedules(ids, attempt) {
  const [schedules, setSchedules] = useState(() => new Map());
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const remaining = ids.split(",");
    const workers = Math.min(3, remaining.length);
    async function load() {
      while (remaining.length && !signal.aborted) {
        const id = remaining.shift();
        const url = "/api/catalog/" + encodeURIComponent(id);
        let schedule = null;
        try {
          if (attempt && cachedPublic(url)?.airing?.warning) forgetPublic(url);
          const detail = await readPublic(url, { signal });
          if (Array.isArray(detail.airing?.episodes) && !detail.airing.warning) schedule = detail.airing;
        } catch {
          // One unavailable schedule does not block the rest of the queue.
        }
        if (!signal.aborted) setSchedules((previous) => new Map(previous).set(id, schedule));
      }
    }
    const currentIds = new Set(remaining);
    setSchedules((previous) => new Map(
      [...previous].filter(([id, schedule]) => currentIds.has(id) && schedule),
    ));
    for (let index = 0; index < workers; index++) void load();
    return () => controller.abort();
  }, [ids, attempt]);
  return schedules;
}

function useQueueProgress(attempt) {
  const [result, setResult] = useState({ records: null, error: false });
  useEffect(() => {
    let controller;
    async function refresh() {
      controller?.abort();
      controller = new AbortController();
      const { signal } = controller;
      try {
        const data = await requestJson("/api/progress", { signal });
        if (!signal.aborted) setResult({ records: new Map(data.items.map((item) => [item.anime_id, item])), error: false });
      } catch {
        if (!signal.aborted) setResult({ records: null, error: true });
      }
    }
    function refreshVisible() {
      if (document.visibilityState === "visible") void refresh();
    }
    void refresh();
    window.addEventListener("focus", refreshVisible);
    window.addEventListener("tsukimi-progress-refresh", refreshVisible);
    return () => {
      controller?.abort();
      window.removeEventListener("focus", refreshVisible);
      window.removeEventListener("tsukimi-progress-refresh", refreshVisible);
    };
  }, [attempt]);
  return result;
}

function ReleaseActions({ anime, episode }) {
  const [availability, setAvailability] = useState("来源待确认");
  const request = useRef(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (availability !== "可播放") return;
    const expiry = setTimeout(() => setAvailability("来源待确认"), 120000);
    return () => clearTimeout(expiry);
  }, [availability]);
  async function check() {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setAvailability("正在确认来源…");
    try {
      const source = await readPlayback(anime.id, episode, null, null, controller.signal);
      if (controller.signal.aborted) return;
      if (source.status === "ready" && typeof source.url === "string" && source.url.trim()) {
        setAvailability("可播放");
      } else if (source.reason === "episode_missing" || source.reason === "no_resources") {
        setAvailability("来源暂缺这一集");
      } else {
        setAvailability("来源暂未确认");
      }
    } catch {
      if (!controller.signal.aborted) setAvailability("来源暂不可用");
    } finally {
      request.current = null;
    }
  }
  return (
    <div className="watching-queue-actions">
      <span className={"watching-queue-availability" + (availability === "可播放" ? " is-playable" : "")} role="status">
        {availability}
      </span>
      <button className="text-button" type="button" onClick={check} disabled={availability === "正在确认来源…"}>
        {availability === "来源待确认" ? "检查来源" : "重新检查"}
      </button>
      <Link className="outline-button" prefetch={false} href={"/watch/" + anime.id + "?episode=" + episode}>看第 {episode} 集 →</Link>
    </div>
  );
}

function QueueRow({ row: { anime, episode, watched }, release = false, today }) {
  const isToday = episode.airdate === today;
  let releaseText = "今日放送";
  if (!isToday) releaseText = release ? "已播出" : "预计 " + formatAiringDate(episode.airdate) + " 播出";
  return (
    <li className="watching-queue-row">
      <Link className="watching-queue-anime" prefetch={false} href={"/anime/" + anime.id}>
        <span className="watching-queue-cover">
          <Image src={anime.cover} alt="" fill sizes="42px" />
        </span>
        <strong>{anime.title}</strong>
      </Link>
      <div className="watching-queue-status">
        <span>{watched ? "上次看到第 " + watched.episode + " 集" : "暂无观看进度"}</span>
        <span>第 {episode.number} 集 · {releaseText}</span>
      </div>
      {release
        ? <ReleaseActions anime={anime} episode={episode.number} />
        : <span className="watching-queue-availability">播出后确认来源</span>}
    </li>
  );
}

export default function WatchingQueue({ items, query }) {
  const [attempt, setAttempt] = useState(0);
  const ids = items.map(({ anime }) => anime.id).sort().join(",");
  const schedules = useSchedules(ids, attempt);
  const { records, error } = useQueueProgress(attempt);
  const today = dateInShanghai();
  const keyword = query.trim().toLowerCase();
  const visible = items.filter(({ anime }) => (
    (anime.title + " " + (anime.originalTitle || "")).toLowerCase().includes(keyword)
  ));
  const { releases, upcoming } = buildWatchingQueue(visible, schedules, records, today);
  const schedulePending = items.some(({ anime }) => !schedules.has(anime.id));
  const recent = releases.filter(({ latestDate }) => latestDate !== today);
  const todayReleases = releases.filter(({ latestDate }) => latestDate === today);
  const scheduleError = items.some(({ anime }) => schedules.get(anime.id) === null);
  return (
    <section className="watching-queue" aria-labelledby="watching-queue-title">
      <h2 id="watching-queue-title">追番待看清单</h2>
      {(schedulePending || (!records && !error)) && (
        <p className="watching-queue-note" role="status">正在核对放送与观看进度…</p>
      )}
      {(scheduleError || error) && (
        <p className="watching-queue-note" role="status">
          {error && scheduleError ? "部分放送与观看记录暂时无法读取。" :
            error ? "观看进度暂时无法读取。" : "部分番剧的放送资料暂时无法确认。"}
          <button type="button" className="text-button" onClick={() => setAttempt((value) => value + 1)}>重试</button>
        </p>
      )}
      <div className="watching-queue-columns">
        <section aria-labelledby="watching-queue-releases">
          <h3 id="watching-queue-releases">有新集</h3>
          {todayReleases.length > 0 && (
            <div className="watching-queue-day">
              <h4>今天</h4>
              <ul>{todayReleases.map((row) => <QueueRow key={row.anime.id + ":" + row.episode.number} row={row} release today={today} />)}</ul>
            </div>
          )}
          {recent.length > 0 && (
            <ul>{recent.map((row) => <QueueRow key={row.anime.id + ":" + row.episode.number} row={row} release today={today} />)}</ul>
          )}
          {!releases.length && !schedulePending && records && <p className="watching-queue-note">暂无确认的新集。</p>}
        </section>
        <section aria-labelledby="watching-queue-upcoming">
          <h3 id="watching-queue-upcoming">即将播出</h3>
          {upcoming.length
            ? upcoming.map(([group, rows]) => (
              <div className="watching-queue-day" key={group}>
                <h4>{group}</h4>
                <ul>{rows.map((row) => <QueueRow key={row.anime.id + ":" + row.episode.number} row={row} today={today} />)}</ul>
              </div>
            ))
            : !schedulePending && <p className="watching-queue-note">暂无确认的下一集排期。</p>}
        </section>
      </div>
    </section>
  );
}
