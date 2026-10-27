"use client";
import { useEffect, useState } from "react";
import { requestJson } from "./api";

export default function useApi(path) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState({ path: "", data: null, error: "" });
  useEffect(() => {
    const controller = new AbortController();
    setResult({ path, data: null, error: "" });
    requestJson(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ path, data, error: "" });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setResult({ path, data: null, error: error.message });
      });
    return () => controller.abort();
  }, [path, attempt]);
  const current = result.path === path ? result : { data: null, error: "" };
  return {
    ...current,
    loading: !current.data && !current.error,
    retry: () => setAttempt((value) => value + 1),
  };
}
