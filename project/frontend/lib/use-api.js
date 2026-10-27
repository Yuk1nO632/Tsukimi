"use client";
import { useEffect, useState } from "react";
import { cachedPublic, forgetPublic, readPublic } from "./public-cache";

export default function useApi(path) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState(() => ({
    path,
    data: cachedPublic(path),
    error: "",
  }));
  useEffect(() => {
    const controller = new AbortController();
    const cached = cachedPublic(path);
    setResult({ path, data: cached, error: "" });
    if (cached) return () => controller.abort();
    readPublic(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ path, data, error: "" });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setResult({ path, data: null, error: error.message });
      });
    return () => controller.abort();
  }, [path, attempt]);
  const current =
    result.path === path ? result : { data: cachedPublic(path), error: "" };
  return {
    ...current,
    loading: !current.data && !current.error,
    retry: () => {
      forgetPublic(path);
      setAttempt((value) => value + 1);
    },
  };
}
