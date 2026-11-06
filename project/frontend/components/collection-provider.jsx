"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useAccount } from "./account-provider";
import { collectionRequest, requestJson } from "../lib/api";

const CollectionContext = createContext(null);
export const collectionLabels = {
  wish: "想看",
  watching: "在看",
  completed: "看完",
};
function validate(data) {
  if (
    !Array.isArray(data?.items) ||
    !data.items.every((item) => item.anime?.id && collectionLabels[item.status])
  )
    throw new Error("追番记录暂时无法读取，请重试。");
  return data.items;
}

export function CollectionProvider({ children }) {
  const account = useAccount();
  return <CollectionState key={account.scope || "connecting"} account={account}>{children}</CollectionState>;
}

function CollectionState({ children, account }) {
  const [collectionItems, setCollectionItems] = useState([]);
  const [status, setStatus] = useState("loading");
  const [loadError, setLoadError] = useState("");
  const [pendingId, setPendingId] = useState(null);
  const [feedback, setFeedback] = useState("");
  const savingRef = useRef(false);
  const readVersion = useRef(0);
  const favoriteIds = collectionItems.map((item) => item.anime.id);
  const reloadCollection = useCallback(async (signal) => {
    if (!account.ready) return;
    const version = ++readVersion.current;
    setStatus((previous) => previous === "ready" ? previous : "loading");
    setLoadError("");
    try {
      const data = validate(await requestJson("/api/collection", { signal }));
      if (signal?.aborted || version !== readVersion.current) return;
      setCollectionItems(data);
      setStatus("ready");
    } catch (error) {
      if (signal?.aborted || version !== readVersion.current) return;
      setLoadError(error.message);
      setStatus("error");
    }
  }, [account.ready]);
  useEffect(() => {
    const controller = new AbortController();
    void reloadCollection(controller.signal);
    const refresh = () => { if (document.visibilityState === "visible" && !savingRef.current) void reloadCollection(); };
    window.addEventListener("focus", refresh);
    window.addEventListener("tsukimi-library-refresh", refresh);
    return () => {
      controller.abort();
      ++readVersion.current;
      window.removeEventListener("focus", refresh);
      window.removeEventListener("tsukimi-library-refresh", refresh);
    };
  }, [reloadCollection]);
  useEffect(() => {
    if (!feedback) return;
    const timer = setTimeout(() => setFeedback(""), 4000);
    return () => clearTimeout(timer);
  }, [feedback]);

  async function setAnimeStatus(id, nextStatus, title = "番剧") {
    if (status !== "ready" || savingRef.current) return false;
    savingRef.current = true;
    setPendingId(id);
    setFeedback("");
    try {
      const items = validate(await collectionRequest(id, nextStatus, account.scope));
      ++readVersion.current;
      // Only confirmed database results replace the displayed state.
      setCollectionItems(items);
      setFeedback(
        nextStatus === null
          ? `已将《${title}》移出片单`
          : `《${title}》已标记为${collectionLabels[nextStatus]}`,
      );
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
  function toggleFavorite(id, title) {
    return setAnimeStatus(id, favoriteIds.includes(id) ? null : "wish", title);
  }
  return (
    <CollectionContext.Provider
      value={{
        collectionItems,
        favoriteIds,
        toggleFavorite,
        setAnimeStatus,
        feedback,
        status,
        loadError,
        pendingId,
        reloadCollection,
      }}
    >
      {children}
    </CollectionContext.Provider>
  );
}
export function useCollection() {
  const value = useContext(CollectionContext);
  if (!value)
    throw new Error("useCollection must be used within CollectionProvider");
  return value;
}
export function CollectionStatus() {
  const { status, loadError, reloadCollection } = useCollection();
  if (status === "ready") return null;
  return (
    <div
      className={`collection-status${status === "error" ? " is-error" : ""}`}
      role={status === "error" ? "alert" : "status"}
    >
      <span>{status === "loading" ? "正在读取追番片单…" : loadError}</span>
      {status === "error" && (
        <button type="button" onClick={() => void reloadCollection()}>
          重新读取片单
        </button>
      )}
    </div>
  );
}
export function CollectionFeedback() {
  const { feedback } = useCollection();
  return (
    <p className="collection-feedback" role="status" aria-live="polite">
      {feedback}
    </p>
  );
}
export function CollectionStatusPicker({ anime }) {
  const { collectionItems, setAnimeStatus, status, pendingId } =
    useCollection();
  const selected =
    collectionItems.find((item) => item.anime.id === anime.id)?.status || "";
  return (
    <select
      className="collection-status-picker"
      aria-label={`《${anime.title}》追番状态`}
      value={selected}
      disabled={status !== "ready" || pendingId !== null}
      onChange={(event) =>
        void setAnimeStatus(anime.id, event.target.value, anime.title)
      }
    >
      <option value="" disabled>
        加入追番片单
      </option>
      {Object.entries(collectionLabels).map(([value, label]) => (
        <option key={value} value={value}>
          {label}
        </option>
      ))}
    </select>
  );
}
