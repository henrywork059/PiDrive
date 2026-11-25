/* Read-only recording library requests. Never abort a mutation. */
(function (root) {
  'use strict';
  function createReader() {
    let generation = 0;
    let controller = null;
    let state = 'unverified';
    function invalidate() {
      generation += 1;
      if (controller) controller.abort();
      controller = null;
      state = 'unverified';
    }
    async function read() {
      invalidate();
      const token = generation;
      const current = new AbortController();
      controller = current;
      state = 'loading';
      const timer = setTimeout(() => current.abort(), 3500);
      try {
        const response = await fetch('/api/recording/items', {cache: 'no-store', signal: current.signal});
        const data = await response.json();
        if (token !== generation) return null;
        if (current.signal.aborted) throw new Error('Read deadline elapsed.');
        const payload = data.payload || data;
        if (!response.ok || data.ok !== true || !Array.isArray(payload.collections?.recordings) ||
            !Array.isArray(payload.collections?.snapshots)) {
          throw new Error(data.message || 'Folder list was not confirmed.');
        }
        state = 'verified';
        return {payload, status: response.status, token};
      } catch (error) {
        if (token !== generation) return null;
        state = 'unverified';
        const message = current.signal.aborted ? 'Folder list timed out.' : String(error.message || error);
        return {error: message, token};
      } finally {
        clearTimeout(timer);
        if (token === generation) controller = null;
      }
    }
    return {read, invalidate, verified: () => state === 'verified',
      loading: () => state === 'loading', isCurrent: token => token === generation};
  }
  root.PiSDRecordingReader = {createReader};
})(typeof window !== 'undefined' ? window : globalThis);
