"use client";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

const scenes = [
  { id: "moonlight", image: "/artwork/moonlight.png", label: "月下放映室", kicker: "MOONLIT STORIES", title: "下一集的故事，\n从这里开始。", description: "把那些闪闪发光的故事，放进自己的追番时光。", accent: "月光与奇幻", query: "奇幻" },
  { id: "seabreeze", image: "/artwork/seabreeze.png", label: "海风来信", kicker: "A LITTLE SUMMER MAGIC", title: "留一点时间，\n给喜欢的日常。", description: "青春、音乐与夏天。总有一个故事，让今天轻盈一点。", accent: "青春与日常", query: "日常" },
  { id: "sunset-train", image: "/artwork/sunset-train.png", label: "黄昏慢行", kicker: "TAKE THE SCENIC ROUTE", title: "旅途还很长，\n喜欢不必散场。", description: "在一段新的旅程里，遇见还没看过的风景。", accent: "治愈与旅行", query: "治愈" },
];

export default function FeaturedHero() {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = scenes[activeIndex];
  function move(offset) { setActiveIndex((previous) => (previous + offset + scenes.length) % scenes.length); }
  return (
    <section className="feature-hero" aria-label="Tsukimi 推荐主题">
      <div className="feature-backdrop" key={active.id}><Image src={active.image} alt="Tsukimi 原创氛围插画" fill priority sizes="100vw" /><div className="feature-shade" /></div>
      <div className="feature-content content-shell"><span className="feature-kicker"><span /> TSUKIMI PICKS · {active.kicker}</span><h1>{active.title}</h1><p>{active.description}</p><div className="hero-actions"><Link className="primary-link" href={`/?q=${encodeURIComponent(active.query)}#library`}><span aria-hidden="true">▶</span> 探索番剧</Link><Link className="hero-secondary" href="/?view=favorites#library">我的追番 ↗</Link></div><div className="hero-art-note">{active.accent}<span>Tsukimi 原创插画</span></div></div>
      <div className="hero-bottom content-shell"><div className="hero-tabs" role="group" aria-label="推荐主题切换">{scenes.map((scene, index) => <button key={scene.id} className={`hero-tab${index === activeIndex ? " is-active" : ""}`} type="button" aria-label={`切换主题：${scene.label}`} aria-pressed={index === activeIndex} onClick={() => setActiveIndex(index)}><Image src={scene.image} alt="" fill sizes="(max-width: 600px) 30vw, 180px" /><span>{scene.label}</span>{index === activeIndex && <i aria-hidden="true">●</i>}</button>)}</div><div className="hero-arrows"><span>0{activeIndex + 1}<i> / 03</i></span><button type="button" onClick={() => move(-1)} aria-label="上一个推荐主题">‹</button><button type="button" onClick={() => move(1)} aria-label="下一个推荐主题">›</button></div></div>
    </section>
  );
}
