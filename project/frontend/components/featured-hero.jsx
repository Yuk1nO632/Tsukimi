"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function FeaturedHero({ items = [], seasonLabel = "本季新番" }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const [hovered, setHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [failedCover, setFailedCover] = useState(null);
  const currentIndex = items.length ? activeIndex % items.length : 0;
  const active = items[currentIndex];

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setReducedMotion(preference.matches);
    const updateVisibility = () => setPageVisible(!document.hidden);
    updateMotion();
    updateVisibility();
    preference.addEventListener("change", updateMotion);
    document.addEventListener("visibilitychange", updateVisibility);
    return () => {
      preference.removeEventListener("change", updateMotion);
      document.removeEventListener("visibilitychange", updateVisibility);
    };
  }, []);

  useEffect(() => {
    if (reducedMotion || !pageVisible || hovered || focusWithin || items.length < 2)
      return;
    const timer = window.setTimeout(() => {
      setActiveIndex((previous) => (previous + 1) % items.length);
    }, 6500);
    return () => window.clearTimeout(timer);
  }, [activeIndex, reducedMotion, pageVisible, hovered, focusWithin, items.length]);

  if (!active) return null;
  const wideCover = active.cover.replace(
    /^https:\/\/lain\.bgm\.tv\/r\/400\/pic\/cover\/l\//,
    "https://lain.bgm.tv/r/1200/pic/cover/l/",
  );
  function move(offset) {
    setActiveIndex(
      (previous) => (previous + offset + items.length) % items.length,
    );
  }

  return (
    <section
      className="featured-hero"
      aria-roledescription="轮播"
      aria-label="当季新番推荐"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocusWithin(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setFocusWithin(false);
        }
      }}
    >
      <picture className="featured-art" aria-hidden="true" key={active.id}>
        {wideCover !== active.cover && failedCover !== wideCover && (
          <source media="(min-width: 701px)" srcSet={wideCover} />
        )}
        <Image
          src={active.cover}
          alt=""
          fill
          loading="eager"
          fetchPriority="high"
          sizes="(max-width: 700px) 100vw, 70vw"
          onError={(event) => {
            if (event.currentTarget.currentSrc === wideCover) setFailedCover(wideCover);
          }}
        />
      </picture>
      <div className="featured-intro content-shell">
        <div className="featured-copy" aria-live="off">
          <p className="featured-season">{seasonLabel}</p>
          <h1>{active.title}</h1>
          <div className="featured-facts">
            {active.releaseDate && <span>{active.releaseDate} 首播</span>}
            {active.category && <span>{active.category}</span>}
          </div>
          <p className="featured-description">{active.description}</p>
          <div className="featured-actions">
            <Link
              prefetch={false}
              className="featured-open"
              href={`/anime/${active.id}`}
            >
              查看番剧 <span aria-hidden="true">↗</span>
            </Link>
            <a href={active.sourceUrl} target="_blank" rel="noreferrer">
              资料与海报 · Bangumi ↗
            </a>
          </div>
        </div>
      </div>
      {items.length > 1 && (
        <div className="featured-picker content-shell">
          <div
            className="featured-navigation"
            role="group"
            aria-label="推荐切换"
          >
            <button
              className="featured-nav-button"
              type="button"
              onClick={() => move(-1)}
              aria-label="上一部新番"
              title="上一部新番"
            >
              <svg
                viewBox="0 0 20 20"
                width="18"
                height="18"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="m12 5-5 5 5 5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
            <span
              className="featured-position"
              aria-label={`第 ${currentIndex + 1} 部，共 ${items.length} 部`}
            >
              <b>{currentIndex + 1}</b>
              <span aria-hidden="true"> / {items.length}</span>
            </span>
            <button
              className="featured-nav-button"
              type="button"
              onClick={() => move(1)}
              aria-label="下一部新番"
              title="下一部新番"
            >
              <svg
                viewBox="0 0 20 20"
                width="18"
                height="18"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="m8 5 5 5-5 5"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
          <div className="featured-choices" role="group" aria-label="切换当季新番">
            {items.map((anime, index) => (
              <button
                key={anime.id}
                className="featured-choice"
                type="button"
                aria-pressed={index === currentIndex}
                onClick={() => setActiveIndex(index)}
              >
                <Image
                  src={anime.cover}
                  alt=""
                  fill
                  sizes="(max-width: 700px) 32vw, 210px"
                />
                <span>{anime.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
