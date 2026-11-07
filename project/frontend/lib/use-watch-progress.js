"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { requestJson } from "./api";
import { useAccount } from "../components/account-provider";

// A route switch waits for the previous player's final save before reading its revision.
const writes = new Map();

export default function useWatchProgress(animeId, episode, source, enabled) {
  const account = useAccount();
  const [state, setState] = useState({
    loading: true,
    position: 0,
    message: "",
    conflict: null,
    error: false,
  });
  const session = useRef(null);
  const loggedIn = !!account.user;
  const sourceRef = useRef(source);
  sourceRef.current = source;

  const flush = useCallback(
    async (current, force = false) => {
      if (!current || !current.ready || current.blocked || !current.snapshot)
        return;
      if (current.sending) {
        if (force) current.flushAgain = true;
        return;
      }
      if (!force && Date.now() - current.lastSave < 10000) return;
      current.sending = true;
      current.lastSave = Date.now();
      const sample = current.snapshot;
      const payload = current.retry || {
        ...sample,
        revision: current.revision,
        operation_id: crypto.randomUUID(),
        scope: current.scope,
      };
      if (!current.retry) current.retrySample = sample;
      current.retry = payload;
      try {
        sessionStorage.setItem(current.storageKey, JSON.stringify(payload));
      } catch {}
      if (current.mounted)
        setState((previous) => ({
          ...previous,
          message: "正在保存进度…",
          error: false,
        }));
      const job = requestJson(`/api/progress/${encodeURIComponent(animeId)}`, {
        method: "PUT",
        keepalive: true,
        headers: {
          "Content-Type": "application/json",
          "X-Tsukimi-Scope": current.scope,
        },
        body: JSON.stringify(payload),
      });
      writes.set(current.key, job);
      try {
        const data = await job;
        current.revision = data.item.revision;
        current.confirmed = data.item;
        current.retry = null;
        if (current.snapshot === current.retrySample) current.snapshot = null;
        current.retrySample = null;
        try {
          sessionStorage.removeItem(current.storageKey);
        } catch {}
        if (current.mounted)
          setState((previous) => ({
            ...previous,
            position: payload.completed ? 0 : payload.position,
            message: loggedIn ? "进度已同步到账号" : "进度已保存到当前浏览器",
            error: false,
          }));
        window.dispatchEvent(new Event("tsukimi-progress-refresh"));
      } catch (failure) {
        if (failure.status === 409) {
          current.blocked = true;
          if (current.mounted)
            setState((previous) => ({
              ...previous,
              conflict: failure.data?.item || null,
              message: failure.data?.item
                ? "另一设备已更新进度，请选择如何继续。"
                : failure.message,
              error: true,
            }));
        } else if (current.mounted)
          setState((previous) => ({
            ...previous,
            message: "进度尚未同步，网络恢复后将重试。",
            error: true,
          }));
      } finally {
        current.sending = false;
        if (writes.get(current.key) === job) writes.delete(current.key);
        const flushAgain = current.flushAgain || !current.mounted;
        current.flushAgain = false;
        if (
          flushAgain &&
          current.snapshot &&
          !current.retry &&
          !current.blocked
        )
          void flush(current, true);
      }
    },
    [animeId, loggedIn],
  );

  useEffect(() => {
    if (!account.ready || !enabled) return;
    const key = `${account.scope}:${animeId}`;
    const current = {
      key,
      scope: account.scope,
      mounted: true,
      ready: false,
      blocked: false,
      sending: false,
      lastSave: 0,
      revision: 0,
      snapshot: null,
      retry: null,
      storageKey: `tsukimi:progress:${key}`,
    };
    session.current = current;
    setState({
      loading: true,
      position: 0,
      message: "正在读取观看进度…",
      conflict: null,
      error: false,
    });
    const controller = new AbortController();
    async function load() {
      try {
        while (writes.has(key)) await writes.get(key)?.catch(() => {});
        const data = await requestJson(
          `/api/progress/${encodeURIComponent(animeId)}`,
          { signal: controller.signal },
        );
        if (!current.mounted) return;
        current.revision = data.item?.revision || 0;
        current.confirmed = data.item;
        current.ready = true;
        let pending = null;
        try {
          pending = JSON.parse(
            sessionStorage.getItem(current.storageKey) || "null",
          );
        } catch {}
        if (pending && pending.scope === current.scope) {
          current.snapshot = pending;
          current.retry = pending;
          current.retrySample = pending;
        }
        const resume = pending?.episode === episode ? pending : data.item;
        setState({
          loading: false,
          position:
            resume?.episode === episode && !resume.completed
              ? resume.position
              : 0,
          message:
            data.item?.episode === episode &&
            !data.item.completed &&
            data.item.position > 0
              ? "已恢复上次观看位置"
              : "播放后自动保存进度",
          conflict: null,
          error: false,
        });
        if (pending) void flush(current, true);
      } catch (failure) {
        if (current.mounted)
          setState({
            loading: false,
            position: 0,
            message: "观看进度读取失败，请重试后开始保存。",
            conflict: null,
            error: true,
          });
      }
    }
    void load();
    const retry = () => {
      if (!current.ready) void load();
      else void flush(current, true);
    };
    const hide = () => {
      if (document.visibilityState === "hidden") void flush(current, true);
    };
    async function focus() {
      if (!current.ready || current.sending || current.blocked) return;
      try {
        const data = await requestJson(
          `/api/progress/${encodeURIComponent(animeId)}`,
          { signal: controller.signal },
        );
        if (
          current.mounted &&
          !current.sending &&
          data.item &&
          data.item.revision > current.revision
        ) {
          current.blocked = true;
          setState((previous) => ({
            ...previous,
            conflict: data.item,
            message: "另一设备已更新进度，请选择如何继续。",
            error: true,
          }));
        }
      } catch {}
    }
    window.addEventListener("focus", focus);
    window.addEventListener("online", retry);
    window.addEventListener("pagehide", retry);
    document.addEventListener("visibilitychange", hide);
    return () => {
      current.mounted = false;
      controller.abort();
      void flush(current, true);
      window.removeEventListener("focus", focus);
      window.removeEventListener("online", retry);
      window.removeEventListener("pagehide", retry);
      document.removeEventListener("visibilitychange", hide);
    };
  }, [account.ready, account.scope, animeId, episode, enabled, flush]);

  function report(sample, force) {
    const current = session.current;
    if (!current?.ready || !enabled || sourceRef.current.status !== "ready")
      return;
    const snapshot = {
      episode,
      ...sample,
      source_provider: sourceRef.current.provider || "anich",
      source_id: sourceRef.current.source_anime_id || null,
      line_id: sourceRef.current.line_id || null,
    };
    const confirmed = current.confirmed;
    if (
      !current.sending &&
      !current.retry &&
      confirmed &&
      ["episode", "position", "duration", "source_provider", "source_id", "line_id"].every(
        (field) => confirmed[field] === snapshot[field],
      ) &&
      Boolean(confirmed.completed) === Boolean(snapshot.completed)
    )
      return;
    current.snapshot = snapshot;
    void flush(current, force);
  }
  function keepLocal() {
    const current = session.current;
    if (!state.conflict || !current) return;
    current.revision = state.conflict.revision;
    current.retry = null;
    current.blocked = false;
    setState((previous) => ({ ...previous, conflict: null, error: false }));
    void flush(current, true);
  }
  function retry() {
    const current = session.current;
    if (!current?.ready || current.blocked) {
      window.location.reload();
      return;
    }
    void flush(current, true);
  }
  return { ...state, report, keepLocal, retry };
}
