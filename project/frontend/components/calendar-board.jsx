"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import useApi from "../lib/use-api";
import { useCollection } from "./collection-provider";
import { LoadFailure } from "./portal-state";
const weekdays = [
  "全部",
  "周一",
  "周二",
  "周三",
  "周四",
  "周五",
  "周六",
  "周日",
];
function today() {
  return (
    ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(
      new Intl.DateTimeFormat("en-US", {
        weekday: "short",
        timeZone: "Asia/Shanghai",
      }).format(new Date()),
    ) + 1
  );
}
export default function CalendarBoard({ compact = false }) {
  const { data, error, loading, retry } = useApi("/api/catalog/calendar");
  const { favoriteIds, status } = useCollection();
  const [day, setDay] = useState(today);
  const [onlySaved, setOnlySaved] = useState(false);
  const [query, setQuery] = useState("");
  const days =
    data?.days.filter((item) => day === 0 || item.weekday === day) || [];
  return (
    <div className={compact ? "calendar-board is-compact" : "calendar-board"}>
      <div className="calendar-toolbar">
        <div className="portal-tabs" role="group" aria-label="放送星期">
          {weekdays.map((label, i) => (
            <button
              type="button"
              key={label}
              aria-pressed={day === i}
              onClick={() => setDay(i)}
            >
              {label}
              {i === today() && <i>今日</i>}
            </button>
          ))}
        </div>
        {!compact && (
          <div className="calendar-tools">
            <input
              aria-label="搜索放送日历"
              placeholder="搜索在播番剧"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <label>
              <input
                type="checkbox"
                checked={onlySaved}
                disabled={status !== "ready"}
                onChange={(event) => setOnlySaved(event.target.checked)}
              />
              只看我的追番
            </label>
          </div>
        )}
      </div>
      {loading ? (
        <div className="portal-loading" role="status">
          正在读取当前放送安排…
        </div>
      ) : error ? (
        <LoadFailure error={error} retry={retry} />
      ) : (
        <>
          <div className="calendar-week">
            {days.map((item) => {
              const items = item.items.filter(
                (anime) =>
                  (!onlySaved || favoriteIds.includes(anime.id)) &&
                  `${anime.title} ${anime.originalTitle}`
                    .toLowerCase()
                    .includes(query.trim().toLowerCase()),
              );
              return (
                <section
                  className="calendar-day"
                  key={item.weekday}
                  aria-label={`${weekdays[item.weekday]}放送`}
                >
                  <div className="calendar-day-heading">
                    <h3>
                      {weekdays[item.weekday]}
                      {item.weekday === today() && <span>今天</span>}
                    </h3>
                    <span>{items.length} 部</span>
                  </div>
                  <div className="schedule-grid">
                    {(compact ? items.slice(0, 6) : items).map((anime) => (
                      <Link
                        className="schedule-card"
                        key={anime.id}
                        href={`/anime/${anime.id}`}
                      >
                        <span className="schedule-cover">
                          <Image src={anime.cover} alt="" fill sizes="70px" />
                        </span>
                        <span>
                          <strong>{anime.title}</strong>
                          <small>{anime.originalTitle}</small>
                          <em>
                            {favoriteIds.includes(anime.id)
                              ? "已加入追番"
                              : "查看番剧详情"}{" "}
                            →
                          </em>
                        </span>
                      </Link>
                    ))}
                    {!items.length && (
                      <p className="calendar-empty">
                        {onlySaved
                          ? "这一天没有追番条目"
                          : "暂无符合条件的放送条目"}
                      </p>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
          <p className="calendar-disclaimer">
            {data.note}{" "}
            {compact && <Link href="/calendar">查看完整日历 →</Link>}
          </p>
        </>
      )}
    </div>
  );
}
