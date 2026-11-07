"use client";
import { useEffect, useRef, useState } from "react";
import { searchPlaybackSource } from "../lib/playback-api";
import PlayerIcon from "./player-icon";

export default function SourceMatcher({
  title,
  provider = "anich",
  onSelect,
  selectedId,
  inputRef,
  initialItems = null,
  selecting = false,
}) {
  const [query, setQuery] = useState(title.slice(0, 80));
  const [items, setItems] = useState(initialItems);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const controllerRef = useRef(null);
  useEffect(() => () => controllerRef.current?.abort(), []);
  useEffect(() => {
    if (Array.isArray(initialItems))
      setItems(
        [...initialItems].sort(
          (a, b) => Number(b.title === title) - Number(a.title === title),
        ),
      );
  }, [initialItems, title]);
  async function search(event) {
    event.preventDefault();
    if (!query.trim()) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true);
    setError("");
    setItems(null);
    try {
      const data = await searchPlaybackSource(query.trim(), controller.signal, provider);
      if (!controller.signal.aborted)
        setItems(
          Array.isArray(data.items)
            ? [...data.items].sort(
                (a, b) =>
                  Number(b.title === query.trim()) -
                  Number(a.title === query.trim()),
              )
            : [],
        );
    } catch (error) {
      if (!controller.signal.aborted)
        setError(error.message || "来源搜索失败，请重试。");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  return (
    <section className="source-matcher" aria-label="搜索播放来源">
      <label className="source-search-label" htmlFor="source-query">
        搜索番名，更换播放来源
      </label>
      <form role="search" aria-label="播放来源搜索" onSubmit={search}>
        <div className="source-search-input">
          <PlayerIcon name="search" size={17} />
          <input
            id="source-query"
            ref={inputRef}
            aria-label="来源搜索关键词"
            placeholder="输入番名或别名"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            maxLength={80}
            required
          />
        </div>
        <button type="submit" disabled={loading || selecting || !query.trim()}>
          {loading ? "搜索中…" : "搜索"}
        </button>
      </form>
      <p className="source-search-hint">
        搜索{provider === "xifan" ? "稀饭动漫" : "AniCh"}，选择前请核对季数与年份。
      </p>
      <div aria-live="polite" aria-busy={loading || selecting}>
        {selecting && (
          <p className="source-search-feedback" role="status">
            正在确认并记住所选来源…
          </p>
        )}
        {loading && (
          <p className="source-search-feedback">正在查找「{query.trim()}」…</p>
        )}
        {error && (
          <p className="source-error" role="alert">
            {error}
          </p>
        )}
        {items?.length === 0 && (
          <p className="source-search-feedback">
            没有找到对应作品，换个别名试试。
          </p>
        )}
        {!!items?.length && (
          <div className="source-result-heading">
            <span>找到 {items.length} 个候选作品</span>
            <button type="button" onClick={() => setItems(null)}>
              收起结果
            </button>
          </div>
        )}
      </div>
      {!!items?.length && (
        <div className="source-results" aria-label="来源搜索结果">
          {items.map((item) => (
            <button
              key={item.id}
              disabled={selecting}
              type="button"
              aria-label={`使用来源：${item.title}`}
              aria-pressed={selectedId === item.id}
              onClick={() => onSelect(item.id, item)}
            >
              <strong>{item.title}</strong>
              <span>
                {item.year || "年份待确认"} ·{" "}
                {item.episodes > 0 ? `${item.episodes} 集` : "集数待确认"}
                <i>{selectedId === item.id ? "当前来源 ✓" : "选择此作品 →"}</i>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
