/* R30: preview freshness uses the client's monotonic clock, never Date.now(). */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PiDrivePreviewFreshness = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function createPreviewFreshness(clock, options = {}) {
    const now = clock || (() => performance.now());
    const delayedMs = options.delayedMs ?? 1500;
    const disconnectedMs = options.disconnectedMs ?? 6000;
    const retryBaseMs = options.retryBaseMs ?? 250;
    const retryMaxMs = options.retryMaxMs ?? 4000;
    let lastSequence = null;
    let lastFrameAt = null;
    let failures = 0;
    let backendLive = null;
    let paused = false;
    function snapshot() {
      const ageMs = lastFrameAt === null ? null : Math.max(0, now() - lastFrameAt);
      const state = paused ? 'Paused'
        : backendLive === false || ageMs === null || ageMs >= disconnectedMs ? 'Disconnected'
        : failures > 0 || ageMs >= delayedMs ? 'Delayed' : 'Live';
      return { state, ageMs, hasFrame: lastFrameAt !== null, failures, sequence: lastSequence };
    }
    return {
      setBackendLive(value) { backendLive = value == null ? null : Boolean(value); },
      setPaused(value) { paused = Boolean(value); },
      isNew(sequence) { return Number.isSafeInteger(sequence) && sequence >= 0 && sequence !== lastSequence; },
      accept(sequence) {
        if (!Number.isSafeInteger(sequence) || sequence < 0 || sequence === lastSequence || backendLive === false) return false;
        lastSequence = sequence;
        lastFrameAt = now();
        failures = 0;
        return true;
      },
      fail() { failures = Math.min(16, failures + 1); },
      snapshot,
      retryDelay(normalDelayMs) {
        if (!failures) return normalDelayMs;
        return Math.max(normalDelayMs, Math.min(retryMaxMs, retryBaseMs * Math.pow(2, Math.min(8, failures - 1))));
      }
    };
  }
  return { createPreviewFreshness };
});
