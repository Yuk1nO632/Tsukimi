"use client";
import { useEffect, useRef, useState } from "react";
import { probeLine, probeLabel } from "../lib/line-probe";

// Recent measurements survive a line switch. No signed URLs or private data saved.
const recent = new Map();
function key(context, line) {
  return `${context}:${line.id}:${line.url ? new URL(line.url).host : "unknown"}`;
}
function cachedResults(context, lines) {
  const result = {};
  for (const line of lines) {
    const entry = recent.get(key(context, line));
    if (entry && Date.now() - entry.at < 60000) result[line.id] = entry.result;
  }
  return result;
}

export default function LineSelector({
  context,
  lines,
  selectedId,
  disabled,
  onSelect,
}) {
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  const [sortByTime, setSortByTime] = useState(false);
  const [message, setMessage] = useState("");
  const controller = useRef(null);
  useEffect(() => {
    setResults(cachedResults(context, lines));
    return () => {
      controller.current?.abort();
      controller.current = null;
    };
  }, [context, lines]);
  async function start() {
    controller.current?.abort();
    const batch = new AbortController();
    controller.current = batch;
    setRunning(true);
    setMessage("");
    setResults({});
    const deadline = setTimeout(() => batch.abort(), 20000);
    const requests = new Map();
    let index = 0;
    let complete = 0;
    async function worker() {
      while (index < lines.length && !batch.signal.aborted) {
        const line = lines[index++];
        setResults((previous) => ({
          ...previous,
          [line.id]: { status: "checking" },
        }));
        if (!requests.has(line.url))
          requests.set(line.url, probeLine(line, batch.signal));
        const result = await requests.get(line.url);
        if (controller.current !== batch) return;
        if (result.status !== "cancelled") {
          complete++;
          setResults((previous) => ({ ...previous, [line.id]: result }));
          if (result.status === "ok") {
            if (recent.size >= 200) recent.delete(recent.keys().next().value);
            recent.set(key(context, line), { at: Date.now(), result });
          }
        }
      }
    }
    await Promise.all([worker(), worker(), worker()]);
    clearTimeout(deadline);
    if (controller.current !== batch) return;
    setResults((previous) =>
      Object.fromEntries(
        Object.entries(previous).filter(
          ([, value]) => value.status !== "checking",
        ),
      ),
    );
    setRunning(false);
    setMessage(
      `已检测 ${complete} / ${lines.length} 条${batch.signal.aborted ? "，其余可重新检测" : ""}`,
    );
  }
  const ordered = [...lines].sort((a, b) =>
    sortByTime
      ? (results[a.id]?.status === "ok"
          ? results[a.id].milliseconds
          : Infinity) -
        (results[b.id]?.status === "ok" ? results[b.id].milliseconds : Infinity)
      : 0,
  );
  return (
    <div className="line-selector">
      <label className="source-line-label">
        播放线路
        <select
          aria-label="播放线路"
          disabled={disabled}
          value={selectedId || ""}
          onChange={(event) => onSelect(Number(event.target.value))}
        >
          {!selectedId && (
            <option value="" disabled>
              请选择线路
            </option>
          )}
          {ordered.map((line) => (
            <option key={line.id} value={line.id}>
              {line.name}
              {results[line.id] ? ` · ${probeLabel(results[line.id])}` : ""}
            </option>
          ))}
        </select>
      </label>
      <details className="line-diagnostics">
        <summary>
          线路响应 <span>查看响应耗时</span>
        </summary>
        <div className="line-probe-actions">
          <button type="button" disabled={disabled || running} onClick={start}>
            {Object.keys(results).length ? "重新检测" : "检测线路"}
          </button>
          {running && (
            <button type="button" onClick={() => controller.current?.abort()}>
              停止检测
            </button>
          )}
          <label>
            <input
              type="checkbox"
              checked={sortByTime}
              onChange={(event) => setSortByTime(event.target.checked)}
            />
            按耗时排序
          </label>
        </div>
        <p className="line-probe-note">
          浏览器到 CDN 的首包耗时，非 ping 或下载速度。不可测不代表不能播放。
        </p>
        <p className="line-probe-status" role="status">
          {running
            ? "正在检测，最多等待 20 秒…"
            : message || "最近成功结果保留 60 秒，点击检测更新。"}
        </p>
        <div
          className="line-probe-list"
          aria-label="线路检测结果"
          aria-busy={running}
        >
          {ordered.map((line) => {
            const result = results[line.id];
            const level =
              result?.status === "ok"
                ? result.milliseconds < 300
                  ? "fast"
                  : result.milliseconds < 1000
                    ? "medium"
                    : "slow"
                : "unknown";
            return (
              <button
                type="button"
                disabled={disabled}
                key={line.id}
                aria-pressed={line.id === selectedId}
                aria-label={`切换线路：${line.name}`}
                onClick={() => onSelect(line.id)}
              >
                <span>
                  {line.name}
                  {line.id === selectedId && <small>正在使用</small>}
                </span>
                <strong className={`line-probe-${level}`}>
                  {probeLabel(result)}
                </strong>
              </button>
            );
          })}
        </div>
      </details>
    </div>
  );
}
