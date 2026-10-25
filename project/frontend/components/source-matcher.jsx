"use client";
import { useEffect, useRef, useState } from "react";
import { searchXifan } from "../lib/playback-api";

export default function SourceMatcher({ title, onSelect }) {
  const [query, setQuery] = useState(title);
  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const controllerRef = useRef(null);
  useEffect(() => () => controllerRef.current?.abort(), []);
  async function search(event) {
    event.preventDefault();
    if (!query.trim()) return;
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setLoading(true); setError(""); setItems(null);
    try {
      const data = await searchXifan(query.trim(), controller.signal);
      if (!controller.signal.aborted) setItems(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      if (!controller.signal.aborted) setError(error.message || "来源搜索失败，请重试。");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }
  return <details className="source-matcher"><summary>搜索 / 重新匹配稀饭来源</summary><p>核对番名、季数和集数，再选择对应作品。</p><form onSubmit={search}><input aria-label="来源搜索关键词" value={query} onChange={(event) => setQuery(event.target.value)} maxLength={80} required /><button type="submit" disabled={loading}>{loading ? "搜索中…" : "搜索来源"}</button></form>{error && <p className="source-error" role="alert">{error}</p>}{items?.length === 0 && <p role="status">没有找到对应作品，试试别名。</p>}<div className="source-results">{items?.map((item) => <button key={item.id} type="button" aria-label={`使用来源：${item.title}`} onClick={() => onSelect(item.id)}><strong>{item.title}</strong><span>{item.year || "年份待确认"} · {item.episodes > 0 ? `${item.episodes} 集` : "集数待确认"}<i>使用此来源 ›</i></span></button>)}</div></details>;
}
