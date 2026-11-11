"use client";

import { useEffect, useRef, useState } from "react";

export default function ThemeSelect() {
  const [choice, setChoice] = useState("system");
  const preference = useRef("system");
  function apply(value) {
    const selected = ["light", "dark"].includes(value) ? value : "system";
    preference.current = selected;
    setChoice(selected);
    const dark = selected === "dark" || (
      selected === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches
    );
    document.documentElement.dataset.theme = dark ? "dark" : "light";
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
  return (
    <select className="theme-select" aria-label="外观模式" title="外观模式" value={choice}
      onChange={(event) => {
        const value = event.target.value;
        apply(value);
        try { localStorage.setItem("tsukimi-theme", value); } catch {}
      }}>
      <option value="system">跟随系统</option>
      <option value="light">浅色模式</option>
      <option value="dark">深色模式</option>
    </select>
  );
}
