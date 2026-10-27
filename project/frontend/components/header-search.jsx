"use client";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { readPublic, cachedPublic } from "../lib/public-cache";
import PlayerIcon from "./player-icon";

export default function HeaderSearch() {
  const initialQuery = useSearchParams().get("q") || "";
  const router = useRouter();
  const rootRef = useRef(null);
  const [query, setQuery] = useState(initialQuery);
  const [open, setOpen] = useState(false);
  const [composing, setComposing] = useState(false);
  const [active, setActive] = useState(-1);
  const [result, setResult] = useState({ query: "", data: null, error: "" });
  const term = query.trim();
  const visible = open && !!term && !composing;
  const data = result.query === term ? result.data : null;
  const items = data?.items?.slice(0, 6) || [];
  const error = result.query === term ? result.error : "";
  const resultsUrl = term ? `/search?q=${encodeURIComponent(term)}` : "/browse";

  useEffect(() => {
    setQuery(initialQuery);
    setOpen(false);
    setActive(-1);
  }, [initialQuery]);
  useEffect(() => {
    function outside(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  useEffect(() => {
    if (!visible) return;
    const path = `/api/catalog?q=${encodeURIComponent(term)}&sort=match&limit=6`;
    const cached = cachedPublic(path);
    if (cached) {
      setResult({ query: term, data: cached, error: "" });
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setResult({ query: term, data: null, error: "" });
      readPublic(path, { signal: controller.signal })
        .then((data) => {
          if (!controller.signal.aborted)
            setResult({ query: term, data, error: "" });
        })
        .catch((error) => {
          if (!controller.signal.aborted)
            setResult({ query: term, data: null, error: error.message });
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [term, visible]);
  useEffect(() => {
    if (active >= 0)
      rootRef.current
        ?.querySelector(`#search-option-${active}`)
        ?.scrollIntoView({ block: "nearest" });
  }, [active]);
  function navigate(url) {
    setOpen(false);
    setActive(-1);
    router.push(url);
  }
  function submit(event) {
    event.preventDefault();
    if (composing) return;
    navigate(resultsUrl);
  }
  function keyboard(event) {
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229)
      return;
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      if (items.length)
        setActive(
          (value) =>
            (value +
              (event.key === "ArrowDown" ? 1 : items.length - 1) +
              items.length) %
            items.length,
        );
    } else if (
      event.key === "Enter" &&
      visible &&
      active >= 0 &&
      items[active]
    ) {
      event.preventDefault();
      navigate(`/anime/${items[active].id}`);
    }
  }
  return (
    <form
      ref={rootRef}
      className="header-search"
      role="search"
      onSubmit={submit}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <input
        name="q"
        aria-label="搜索番剧资料"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={visible}
        aria-controls={visible ? "header-search-options" : undefined}
        aria-activedescendant={
          visible && active >= 0 && items[active]
            ? `search-option-${active}`
            : undefined
        }
        autoComplete="off"
        maxLength={100}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        onKeyDown={keyboard}
        onCompositionStart={() => {
          setComposing(true);
          setActive(-1);
        }}
        onCompositionEnd={(event) => {
          setQuery(event.currentTarget.value);
          setComposing(false);
        }}
        placeholder="搜索番名、原名或别名"
      />
      <button
        className="header-search-submit"
        type="submit"
        aria-label="搜索番剧"
      >
        <PlayerIcon name="search" size={19} />
      </button>
      {visible && (
        <div className="header-search-dropdown">
          <div className="search-suggest-heading">
            <span>相关番剧</span>
            <small>点击直接查看详情</small>
          </div>
          <div
            id="header-search-options"
            role="listbox"
            aria-label="番剧搜索建议"
          >
            {!data && !error && (
              <p className="search-suggest-message" role="status">
                正在查找…
              </p>
            )}
            {error && (
              <p className="search-suggest-message" role="status">
                {error} 可点击下方查看完整搜索。
              </p>
            )}
            {data && !items.length && (
              <p className="search-suggest-message" role="status">
                暂无相关番剧，试试别名。
              </p>
            )}
            {items.map((anime, index) => (
              <Link
                prefetch={false}
                role="option"
                id={`search-option-${index}`}
                aria-selected={active === index}
                tabIndex={-1}
                href={`/anime/${anime.id}`}
                key={anime.id}
                className="search-suggest-option"
                onPointerMove={() => setActive(index)}
                onClick={() => {
                  setOpen(false);
                  setActive(-1);
                }}
              >
                <span className="search-suggest-cover">
                  <Image src={anime.cover} alt="" fill sizes="40px" />
                </span>
                <span className="search-suggest-copy">
                  <strong>{anime.title}</strong>
                  <small>
                    {anime.year || "年份待定"} · {anime.platform || "动画"} ·{" "}
                    {anime.episodes ? `${anime.episodes} 集` : "集数待定"}
                  </small>
                </span>
                <span className="search-suggest-score">
                  {anime.score > 0 ? anime.score.toFixed(1) : ""}
                </span>
              </Link>
            ))}
          </div>
          <Link
            prefetch={false}
            className="search-suggest-all"
            href={resultsUrl}
            onClick={() => {
              setOpen(false);
              setActive(-1);
            }}
          >
            查看“{term}”的全部结果 →
          </Link>
        </div>
      )}
    </form>
  );
}
