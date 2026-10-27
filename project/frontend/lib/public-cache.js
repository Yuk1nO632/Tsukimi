import { requestJson } from "./api";
const entries = new Map();
const TTL = 60000;
export function publicKey(path) {
  const url = new URL(path, "http://tsukimi.local");
  if (url.pathname === "/api/catalog") {
    if (!url.searchParams.has("page")) url.searchParams.set("page", "1");
    if (!url.searchParams.has("limit")) url.searchParams.set("limit", "18");
    if (!url.searchParams.has("sort")) url.searchParams.set("sort", "heat");
  }
  url.searchParams.sort();
  return `${url.pathname}${url.search ? url.search : ""}`;
}
export function cachedPublic(path) {
  if (!path.startsWith("/api/catalog")) return null;
  const key = publicKey(path);
  const entry = entries.get(key);
  if (!entry || entry.expires <= Date.now()) {
    entries.delete(key);
    return null;
  }
  return entry.data;
}
export function forgetPublic(path) {
  entries.delete(publicKey(path));
}
export async function readPublic(path, options = {}) {
  if (!path.startsWith("/api/catalog")) return requestJson(path, options);
  const cached = cachedPublic(path);
  if (cached) return cached;
  const key = publicKey(path);
  const data = await requestJson(key, options);
  if (!options.signal?.aborted) {
    if (entries.size >= 40) entries.delete(entries.keys().next().value);
    entries.set(key, { data, expires: Date.now() + TTL });
  }
  return data;
}
