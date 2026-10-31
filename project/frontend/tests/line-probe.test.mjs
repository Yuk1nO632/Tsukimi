import { test } from "node:test";
import assert from "node:assert/strict";
import { probeLine, probeLabel } from "../lib/line-probe.js";

function response({ status = 206, headers = {}, empty = false } = {}) {
  let reads = 0,
    cancels = 0;
  return {
    value: {
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers(headers),
      body: {
        cancel: async () => {
          cancels++;
        },
        getReader: () => ({
          read: async () => {
            reads++;
            return {
              done: empty,
              value: empty ? undefined : new Uint8Array(1024),
            };
          },
          cancel: async () => {
            cancels++;
          },
        }),
      },
    },
    reads: () => reads,
    cancels: () => cancels,
  };
}
const line = {
  url: "https://cdn.example.com/test.mp4?temporary=fixture",
  format: "mp4",
};

test("range request returns timing only, with no file-size metadata", async (t) => {
  const sample = response({ headers: { "Content-Length": "1024" } });
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url, line.url);
    assert.equal(options.headers.Range, "bytes=0-1023");
    assert.equal(options.credentials, "omit");
    return sample.value;
  });
  const result = await probeLine(line);
  assert.equal(result.status, "ok");
  assert.equal("bytes" in result, false);
  assert.equal(sample.reads(), 1);
  assert.equal(sample.cancels(), 1);
  assert.ok(result.milliseconds >= 1);
});
test("ignored range is closed after first chunk instead of downloading the movie", async (t) => {
  const sample = response({
    status: 200,
    headers: { "Content-Length": "419430400" },
  });
  t.mock.method(globalThis, "fetch", async () => sample.value);
  assert.equal((await probeLine(line)).status, "ok");
  assert.equal(sample.reads(), 1);
  assert.equal(sample.cancels(), 1);
});
test("CORS/network failures are unmeasurable, not dead playback lines", async (t) => {
  t.mock.method(globalThis, "fetch", async () => {
    throw new TypeError("Failed to fetch");
  });
  const result = await probeLine(line);
  assert.equal(result.status, "unmeasurable");
  assert.equal(probeLabel(result), "不可测");
});
test("user cancellation never becomes a timeout result", async (t) => {
  const controller = new AbortController();
  controller.abort();
  t.mock.method(globalThis, "fetch", async () => {
    throw new DOMException("Aborted", "AbortError");
  });
  assert.equal((await probeLine(line, controller.signal)).status, "cancelled");
});
test("HTTP errors and empty bodies have no success latency", async (t) => {
  const sample = response({ status: 403 });
  t.mock.method(globalThis, "fetch", async () => sample.value);
  assert.deepEqual(await probeLine(line), { status: "http", code: 403 });
  assert.equal(sample.cancels(), 1);
  const empty = response({ empty: true });
  globalThis.fetch = async () => empty.value;
  assert.deepEqual(await probeLine(line), { status: "empty" });
  assert.equal(empty.cancels(), 1);
});
