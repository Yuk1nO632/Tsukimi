"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

export default function FeaturedHero({ items = [], seasonLabel = "本季新番" }) {
  const tabsRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const active = items[activeIndex % items.length];

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
    if (reducedMotion || !pageVisible || items.length < 2) return;
    const timer = window.setTimeout(() => {
      setActiveIndex((previous) => (previous + 1) % items.length);
    }, 6500);
    return () => window.clearTimeout(timer);
  }, [activeIndex, reducedMotion, pageVisible, items.length]);

  useEffect(() => {
    const rail = tabsRef.current;
    const button = rail?.children[activeIndex % items.length];
    if (!button) return;
    const revealSelection = () => rail.scrollTo({
      left: button.offsetLeft - (rail.clientWidth - button.offsetWidth) / 2,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
    revealSelection();
    const observer = new ResizeObserver(revealSelection);
    observer.observe(rail);
    return () => observer.disconnect();
  }, [activeIndex, items.length]);

  if (!active) return null;
  function move(offset) {
    setActiveIndex(
      (previous) => (previous + offset + items.length) % items.length,
    );
  }

  return (
    <section
      className="season-hero"
      aria-roledescription="轮播"
      aria-label="当季新番推荐"
    >
      <div className="season-backdrop" aria-hidden="true" key={active.id}>
        <Image
          src={active.cover}
          alt=""
          fill
          loading="eager"
          fetchPriority="high"
          sizes="100vw"
        />
      </div>
      <div className="season-inner content-shell">
        <div className="season-copy" aria-live="off">
          <span className="season-kicker">
            <i /> {seasonLabel}
          </span>

          <h1>{active.title}</h1>
          <div className="season-facts">
            <span>{active.releaseDate} 首播</span>
            <span>{active.category}</span>
          </div>
          <p className="season-description">{active.description}</p>
          <div className="hero-actions">
            <Link
              prefetch={false}
              className="primary-link"
              href={`/anime/${active.id}`}
            >
              查看番剧 <span aria-hidden="true">↗</span>
            </Link>
            <Link
              prefetch={false}
              className="hero-secondary"
              href="/collection"
            >
              我的追番
            </Link>
          </div>
          <a
            className="season-source"
            href={active.sourceUrl}
            target="_blank"
            rel="noreferrer"
          >
            资料与海报来源：Bangumi ↗
          </a>
        </div>
        <Link
          prefetch={false}
          className="season-keyvisual"
          href={`/anime/${active.id}`}
          aria-label={`查看《${active.title}》详情`}
        >
          <Image
            key={active.id}
            src={active.cover}
            alt={`${active.title} 海报`}
            fill
            loading="eager"
            fetchPriority="high"
            sizes="(max-width: 600px) 38vw, 300px"
          />
        </Link>
      </div>
      <div className="season-bottom content-shell">
        <div
          className="season-tabs"
          ref={tabsRef}
          role="group"
          aria-label="切换当季新番"
        >
          {items.map((anime, index) => (
            <button
              key={anime.id}
              className={`season-tab${index === activeIndex ? " is-active" : ""}`}
              type="button"
              aria-label={`推荐：${anime.title}`}
              aria-pressed={index === activeIndex}
              onClick={() => setActiveIndex(index)}
            >
              <span className="season-tab-cover">
                <Image src={anime.cover} alt="" fill sizes="48px" />
              </span>
              <span className="season-tab-copy">
                <small>推荐 {index + 1}</small>
                <strong>{anime.title}</strong>
              </span>
              {index === activeIndex && <i aria-hidden="true">●</i>}
            </button>
          ))}
        </div>
        {items.length > 1 && (
          <div className="season-controls">
            <div
              className="season-navigation"
              role="group"
              aria-label="推荐切换"
            >
              <span
                className="season-position"
                aria-label={`第 ${activeIndex + 1} 部，共 ${items.length} 部`}
              >
                <b>{String(activeIndex + 1).padStart(2, "0")}</b>
                <span aria-hidden="true">
                  {" "}
                  / {String(items.length).padStart(2, "0")}
                </span>
              </span>
              <button
                className="season-nav-button"
                type="button"
                onClick={() => move(-1)}
                aria-label="上一部新番"
                title="上一部新番"
              >
                <svg
                  viewBox="0 0 20 20"
                  width="16"
                  height="16"
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
                上一部
              </button>
              <button
                className="season-nav-button"
                type="button"
                onClick={() => move(1)}
                aria-label="下一部新番"
                title="下一部新番"
              >
                下一部
                <svg
                  viewBox="0 0 20 20"
                  width="16"
                  height="16"
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
          </div>
        )}
      </div>
    </section>
  );
}
