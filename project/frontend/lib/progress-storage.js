export function discardLocalProgress(current, storage) {
  // Block unload/visibility saves before removing the pending retry.
  current.ready = false;
  current.blocked = true;
  current.snapshot = null;
  current.retry = null;
  current.retrySample = null;
  current.flushAgain = false;
  try {
    storage.removeItem(current.storageKey);
  } catch {}
}
