import test from 'node:test';
import assert from 'node:assert/strict';
import { discardLocalProgress } from '../lib/progress-storage.js';

test('choosing cloud progress removes the stale retry before unload can save it', () => {
  const current = {
    ready: true,
    blocked: false,
    snapshot: { position: 180 },
    retry: { revision: 1 },
    retrySample: { position: 180 },
    flushAgain: true,
    storageKey: 'progress:user:anime',
  };
  const removed = [];
  discardLocalProgress(current, { removeItem: key => removed.push(key) });
  assert.equal(current.ready, false);
  assert.equal(current.blocked, true);
  assert.equal(current.snapshot, null);
  assert.equal(current.retry, null);
  assert.equal(current.retrySample, null);
  assert.equal(current.flushAgain, false);
  assert.deepEqual(removed, ['progress:user:anime']);
});

test('unavailable browser storage still disables stale progress writes', () => {
  const current = {
    ready: true,
    blocked: false,
    snapshot: { position: 180 },
    retry: { revision: 1 },
  };
  discardLocalProgress(current, {
    removeItem: () => { throw new Error('storage disabled'); },
  });
  assert.equal(current.ready, false);
  assert.equal(current.retry, null);
  assert.equal(current.snapshot, null);
});
