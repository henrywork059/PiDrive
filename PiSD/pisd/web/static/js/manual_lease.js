/* F2: a renewal can extend live output but never replay a command. */
(function (root) {
  'use strict';
  function create({ active, onLost, fetchImpl = (...args) => root.fetch(...args) }) {
    let epoch = 0, seq = 0, pending = 0, token = null, renewing = false;
    function cancel() { epoch += 1; pending = 0; token = null; }
    function begin() { pending += 1; return { epoch, seq: ++seq }; }
    function finish(ticket, result) {
      if (ticket.epoch !== epoch) return;
      pending = Math.max(0, pending - 1);
      if (ticket.seq !== seq) return;
      if (!result || result.ok !== true) { lose(); return; }
      token = typeof result.manual_lease_id === 'string' ? result.manual_lease_id : null;
    }
    function lose() {
      cancel();
      onLost();
    }
    async function tick() {
      if (!token || pending || renewing) return;
      if (!active()) { cancel(); return; }
      const currentEpoch = epoch, currentToken = token;
      renewing = true;
      try {
        const response = await fetchImpl('/api/control/heartbeat', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lease_id: currentToken }), cache: 'no-store'
        });
        const result = await response.json();
        if (currentEpoch === epoch && currentToken === token && (!response.ok || result.ok !== true)) lose();
      } catch (_) {
        if (currentEpoch === epoch && currentToken === token) lose();
      } finally { renewing = false; }
    }
    const timer = root.setInterval(tick, 250);
    return { begin, finish, cancel, tick, close() { cancel(); root.clearInterval(timer); } };
  }
  root.PiSDManualLease = { create };
})(typeof window !== 'undefined' ? window : globalThis);
