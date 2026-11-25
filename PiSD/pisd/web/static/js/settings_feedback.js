/* R31 — client-only settings confirmation states; no persistence or runtime side effects. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PiDriveSettingsFeedback = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function matchesSubset(expected, actual) {
    if (typeof expected === 'number') {
      return typeof actual === 'number' && Number.isFinite(expected) && Number.isFinite(actual)
        && Math.abs(expected - actual) <= 0.00001;
    }
    if (Array.isArray(expected)) {
      return Array.isArray(actual) && expected.length === actual.length
        && expected.every((value, i) => matchesSubset(value, actual[i]));
    }
    if (expected && typeof expected === 'object') {
      return actual !== null && typeof actual === 'object' && !Array.isArray(actual)
        && Object.keys(expected).every(key => Object.prototype.hasOwnProperty.call(actual, key)
          && matchesSubset(expected[key], actual[key]));
    }
    return Object.is(expected, actual);
  }

  function createSettingsFeedback() {
    let revision = 0;
    let busy = false;
    let phase = 'Unsaved';
    let detail = 'Settings have not been confirmed by the backend.';
    return {
      snapshot() { return { phase, detail, busy, revision, retry: phase === 'Failed' }; },
      edit() {
        revision += 1;
        phase = 'Unsaved';
        detail = 'Changes are not yet confirmed.';
        return revision;
      },
      begin(options = {}) {
        if (busy) return null;
        busy = true;
        phase = options.phase || 'Applying';
        detail = options.detail || 'Waiting for backend response and readback.';
        return revision;
      },
      complete(token, verified, message = '', applied = true) {
        busy = false;
        if (token !== revision) {
          phase = 'Unsaved';
          detail = 'Settings changed while the request was running. Apply again.';
          return false;
        }
        phase = verified ? (applied ? 'Applied' : 'Unsaved') : 'Failed';
        detail = message || (verified ? 'Backend confirmed.' : 'Backend did not confirm the settings.');
        return verified;
      },
      fail(token, error) {
        return this.complete(token, false, String(error || 'Backend operation failed.'));
      }
    };
  }
  return { matchesSubset, createSettingsFeedback };
});
