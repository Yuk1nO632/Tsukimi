"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { requestJson } from "../lib/api";

const AccountContext = createContext(null);

export function AccountProvider({ children }) {
  const [account, setAccount] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const readVersion = useRef(0);
  const actionBusy = useRef(false);
  const reading = useRef(null);
  const reload = useCallback(async () => {
    if (actionBusy.current) return;
    if (reading.current) return reading.current;
    const version = ++readVersion.current;
    const job = requestJson("/api/account");
    reading.current = job;
    try {
      const data = await job;
      if (version !== readVersion.current) return;
      setAccount(data);
      setError("");
      return data;
    } catch (failure) {
      if (version === readVersion.current) setError(failure.message);
    } finally {
      if (reading.current === job) reading.current = null;
    }
  }, []);
  useEffect(() => {
    void reload();
    const focus = () => {
      if (document.visibilityState === "visible") void reload();
    };
    window.addEventListener("focus", focus);
    document.addEventListener("visibilitychange", focus);
    return () => {
      window.removeEventListener("focus", focus);
      document.removeEventListener("visibilitychange", focus);
    };
  }, [reload]);

  async function action(path, payload) {
    if (actionBusy.current) throw new Error("正在处理，请稍候。");
    actionBusy.current = true;
    setBusy(true);
    ++readVersion.current;
    try {
      await reading.current?.catch(() => {});
      const data = await requestJson(`/api/account/${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(account?.scope ? { "X-Tsukimi-Scope": account.scope } : {}),
        },
        body: JSON.stringify(payload || {}),
      });
      if (data.scope) setAccount(data);
      if (["logout", "password", "reset-password"].includes(path)) {
        const fresh = await requestJson("/api/account");
        setAccount(fresh);
      }
      setError("");
      return data;
    } finally {
      actionBusy.current = false;
      setBusy(false);
    }
  }

  return (
    <AccountContext.Provider
      value={{ ...account, ready: !!account, error, busy, action, reload }}
    >
      {children}
    </AccountContext.Provider>
  );
}

export function useAccount() {
  const account = useContext(AccountContext);
  if (!account) throw new Error("useAccount requires AccountProvider");
  return account;
}
