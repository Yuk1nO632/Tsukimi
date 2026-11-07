import assert from 'node:assert/strict';
import test from 'node:test';
import { readPlayback, searchPlaybackSource, rememberSource } from '../lib/playback-api.js';

test('automatic playback and scoped xifan identifiers use separate query parameters', async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push([url, options]);
    return new Response(JSON.stringify({ status: 'ready' }));
  };
  try {
    await readPlayback('bgm-386809', 1, null, null);
    await readPlayback('bgm-386809', 2, 588, 5, undefined, 'xifan');
    const automatic = new URL(calls[0][0], 'http://localhost');
    const scoped = new URL(calls[1][0], 'http://localhost');
    assert.equal(automatic.searchParams.get('source_provider'), 'auto');
    assert.equal(automatic.searchParams.has('source_anime_id'), false);
    assert.equal(scoped.searchParams.get('source_provider'), 'xifan');
    assert.equal(scoped.searchParams.get('source_anime_id'), '588');
    assert.equal(scoped.searchParams.get('line_id'), '5');
  } finally {
    globalThis.fetch = original;
  }
});

test('source search and remembered choices stay scoped to the selected provider', async () => {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    calls.push([url, options]);
    return new Response(JSON.stringify({ provider: 'xifan' }));
  };
  try {
    await searchPlaybackSource('【我推的孩子】', undefined, 'xifan');
    await rememberSource('bgm-386809', 588, undefined, 'xifan');
    assert.ok(calls[0][0].startsWith('/api/sources/xifan/search?'));
    assert.equal(calls[1][0], '/api/sources/xifan/bindings/bgm-386809');
    assert.equal(calls[1][1].method, 'PUT');
    assert.deepEqual(JSON.parse(calls[1][1].body), { source_anime_id: 588 });
  } finally {
    globalThis.fetch = original;
  }
});
