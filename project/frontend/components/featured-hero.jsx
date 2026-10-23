"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { featuredAnime, catalogMeta } from "../lib/anime";

export default function FeaturedHero() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(true);
  const active = featuredAnime[activeIndex];

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
    if (paused || hovered || focused || reducedMotion || !pageVisible || featuredAnime.length < 2) return;
    const timer = window.setTimeout(() => {
      setActiveIndex((previous) => (previous + 1) % featuredAnime.length);
    }, 6500);
    return () => window.clearTimeout(timer);
  }, [activeIndex, paused, hovered, focused, reducedMotion, pageVisible]);

  if (!active) return null;
  function move(offset) {
    setActiveIndex((previous) => (previous + offset + featuredAnime.length) % featuredAnime.length);
  }

  return (
    <section className="season-hero" aria-roledescription="轮播" aria-label="当季新番推荐"
      onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}
      onFocusCapture={() => setFocused(true)}
      onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false); }}>
      <div className="season-backdrop" aria-hidden="true" key={active.id}>
        <Image src={active.cover} alt="" fill priority sizes="100vw" />
      </div>
      <div className="season-inner content-shell">
        <div className="season-copy" aria-live="off">
          <span className="season-kicker"><i /> {catalogMeta.featuredSeason.label}</span>
          <p className="season-eyebrow">THIS SEASON, YOUR NEXT STORY.</p>
          <h1>{active.title}</h1>
          <div className="season-facts"><span>{active.releaseDate} 首播</span><span>{active.category}</span></div>
          <p className="season-description">{active.description}</p>
          <div className="hero-actions"><Link className="primary-link" href={`/anime/${active.id}`}>查看番剧 <span aria-hidden="true">↗</span></Link><Link className="hero-secondary" href="/?view=favorites#library">我的追番</Link></div>
          <a className="season-source" href={active.sourceUrl} target="_blank" rel="noreferrer">资料与海报来源：Bangumi ↗</a>
        </div>
        <Link className="season-keyvisual" href={`/anime/${active.id}`} aria-label={`查看《${active.title}》详情`}>
          <Image key={active.id} src={active.cover} alt={`${active.title} 海报`} fill priority sizes="(max-width: 600px) 38vw, 300px" />
        </Link>
      </div>
      <div className="season-bottom content-shell">
        <div className="season-tabs" role="group" aria-label="切换当季新番">
          {featuredAnime.map((anime, index) => (
            <button key={anime.id} className={`season-tab${index === activeIndex ? " is-active" : ""}`} type="button"
              aria-label={`推荐：${anime.title}`} aria-pressed={index === activeIndex} onClick={() => setActiveIndex(index)}>
              <span className="season-tab-cover"><Image src={anime.cover} alt="" fill sizes="48px" /></span>
              <span className="season-tab-copy"><small>0{index + 1} / 秋季新番</small><strong>{anime.title}</strong></span>
              {index === activeIndex && <i aria-hidden="true">●</i>}
            </button>
          ))}
        </div>
        <div className="season-controls"><span>{String(activeIndex + 1).padStart(2, "0")} <i>/ {String(featuredAnime.length).padStart(2, "0")}</i></span><button type="button" onClick={() => move(-1)} aria-label="上一部新番">‹</button><button type="button" onClick={() => move(1)} aria-label="下一部新番">›</button><button className="season-pause" type="button" aria-label={paused ? "继续自动轮播" : "暂停自动轮播"} aria-pressed={paused} onClick={() => setPaused((previous) => !previous)}>{paused ? "▷" : "Ⅱ"}</button></div>
      </div>
    </section>
  );
}
