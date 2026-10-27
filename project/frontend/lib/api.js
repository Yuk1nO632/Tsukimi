export async function requestJson(path, options = {}) {
  const timeout = AbortSignal.timeout(22000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  let response;
  try {
    response = await fetch(path, {
      ...options,
      signal,
      cache: "no-store",
      credentials: "same-origin",
    });
  } catch {
    throw new Error("暂时无法连接服务，请重试。");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(
      data?.detail && typeof data.detail === "string"
        ? data.detail
        : "请求未完成，请稍后重试。",
    );
    error.status = response.status;
    throw error;
  }
  if (!data || typeof data !== "object")
    throw new Error("返回的数据暂时无法读取。");
  return data;
}

export function collectionRequest(id, status) {
  return requestJson(
    `/api/collection/${encodeURIComponent(id)}`,
    status === null
      ? { method: "DELETE" }
      : {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
  );
}
