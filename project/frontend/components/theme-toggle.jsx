"use client";

import { useEffect, useRef, useState } from "react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const preference = useRef("system");
  function apply(value) {
    const selected = ["light", "dark"].includes(value) ? value : "system";
    preference.current = selected;
    const dark = selected === "dark" || (
      selected === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches
    );
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    setDark(dark);
  }
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const read = () => {
      let saved = "system";
      try { saved = localStorage.getItem("tsukimi-theme") || "system"; } catch {}
      apply(saved);
    };
    const systemChanged = () => {
      if (preference.current === "system") apply("system");
    };
    const storageChanged = (event) => {
      if (event.key === "tsukimi-theme" || event.key === null) read();
    };
    read();
    media.addEventListener("change", systemChanged);
    window.addEventListener("storage", storageChanged);
    return () => {
      media.removeEventListener("change", systemChanged);
      window.removeEventListener("storage", storageChanged);
    };
  }, []);
  const label = dark ? "切换浅色模式" : "切换深色模式";
  return (
    <button
      className="theme-toggle"
      type="button"
      aria-label={label}
      aria-pressed={dark}
      title={label}
      onClick={() => {
        const value = dark ? "light" : "dark";
        apply(value);
        try { localStorage.setItem("tsukimi-theme", value); } catch {}
      }}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <g className="theme-sun"><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" /></g>
        <path className="theme-moon" d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7Z" />
      </svg>
    </button>
  );
}
