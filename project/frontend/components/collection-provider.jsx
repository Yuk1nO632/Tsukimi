"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { getAnime } from "../lib/anime";
import { readFavorites, writeFavorite } from "../lib/collection-api";

const CollectionContext = createContext(null);

// React state displays the latest confirmed result. SQLite now stores the durable copy.
export function CollectionProvider({ children }) {
  const [favoriteIds, setFavoriteIds] = useState([]);
  const [status, setStatus] = useState("loading");
  const [loadError, setLoadError] = useState("");
  const [pendingId, setPendingId] = useState(null);
  const [feedback, setFeedback] = useState("");
  const savingRef = useRef(false);
  const readVersion = useRef(0);

  const reloadCollection = useCallback(async (signal) => {
    const version = ++readVersion.current;
    setStatus("loading");
    setLoadError("");
    try {
      const ids = await readFavorites(signal);
      if (signal?.aborted || version !== readVersion.current) return;
      setFavoriteIds(ids);
      setStatus("ready");
    } catch (error) {
      if (signal?.aborted || version !== readVersion.current) return;
      setLoadError(error.message);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void reloadCollection(controller.signal);
    return () => controller.abort();
  }, [reloadCollection]);

  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(""), 4000);
    return () => clearTimeout(timer);
  }, [feedback]);

  async function toggleFavorite(id) {
    const anime = getAnime(id);
    if (!anime || status !== "ready" || savingRef.current) return false;
    const wasFavorite = favoriteIds.includes(id);
    savingRef.current = true;
    setPendingId(id);
    setFeedback("");
    try {
      const ids = await writeFavorite(id, !wasFavorite);
      // Update only after the server confirms persistence; a failed request keeps the old state.
      setFavoriteIds(ids);
      setFeedback(wasFavorite ? `已取消收藏《${anime.title}》。` : `已收藏《${anime.title}》。`);
      return true;
    } catch (error) {
      setFeedback(error.message);
      if (error.status === 401) {
        setLoadError(error.message);
        setStatus("error");
      }
      return false;
    } finally {
      savingRef.current = false;
      setPendingId(null);
    }
  }

  return (
    <CollectionContext.Provider value={{ favoriteIds, toggleFavorite, feedback, status, loadError, pendingId, reloadCollection }}>
      {children}
    </CollectionContext.Provider>
  );
}

export function useCollection() {
  const collection = useContext(CollectionContext);
  if (!collection) throw new Error("useCollection must be used within CollectionProvider");
  return collection;
}

export function CollectionStatus() {
  const { status, loadError, reloadCollection } = useCollection();
  if (status === "ready") return null;
  return <div className={`collection-status${status === "error" ? " is-error" : ""}`} role={status === "error" ? "alert" : "status"}><span>{status === "loading" ? "正在读取你的追番记录…" : loadError}</span>{status === "error" && <button type="button" onClick={() => void reloadCollection()}>重新读取收藏</button>}</div>;
}

export function CollectionFeedback() {
  const { feedback } = useCollection();
  return <p className="collection-feedback" role="status" aria-live="polite">{feedback}</p>;
}
