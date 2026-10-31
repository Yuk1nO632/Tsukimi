// Browser-to-CDN first-byte measurement. Never proxy video through FastAPI.
export async function probeLine(line, signal) {
  if (typeof line.url !== "string") return { status: "unmeasurable" };
  const started = performance.now();
  const timeout = AbortSignal.timeout(4500);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  let reader;
  try {
    const response = await fetch(line.url, {
      method: "GET",
      mode: "cors",
      credentials: "omit",
      cache: "no-store",
      referrerPolicy: "no-referrer",
      headers: { Range: "bytes=0-1023" },
      signal: combined,
    });
    if (!response.ok) {
      await response.body?.cancel();
      return { status: "http", code: response.status };
    }
    reader = response.body?.getReader();
    const chunk = await reader?.read();
    if (!chunk || chunk.done || !chunk.value?.byteLength)
      return { status: "empty" };
    const milliseconds = Math.max(1, Math.round(performance.now() - started));
    return { status: "ok", milliseconds };
  } catch {
    if (signal?.aborted) return { status: "cancelled" };
    return { status: timeout.aborted ? "timeout" : "unmeasurable" };
  } finally {
    // Do not consume the rest, even when a CDN ignores the Range request.
    await reader?.cancel().catch(() => {});
  }
}

export function probeLabel(result) {
  if (!result) return "未检测";
  if (result.status === "checking") return "检测中…";
  if (result.status === "ok") return `${result.milliseconds} ms`;
  if (result.status === "http") return `HTTP ${result.code}`;
  if (result.status === "timeout") return "超时";
  if (result.status === "empty") return "空响应";
  if (result.status === "cancelled") return "未检测";
  return "不可测";
}
