(() => {
  'use strict';

  const STOP_COOLDOWN_MS = 300;
  let lastStopAt = 0;

  function shouldIgnoreSpace(event) {
    if (event.key !== ' ') return true;
    const active = document.activeElement;
    const target = event.target;
    const element = active && active !== document.body ? active : target;
    if (!element || element === document.body || element === document.documentElement) return false;
    if (element.closest?.('[data-space-stop-ignore="true"]')) return true;
    const tag = String(element.tagName || '').toLowerCase();
    if (tag === 'textarea' || tag === 'select') return true;
    if (tag === 'input') {
      const type = String(element.type || '').toLowerCase();
      return !['button', 'checkbox', 'radio', 'submit', 'reset'].includes(type);
    }
    return Boolean(element.isContentEditable);
  }

  function postJson(path, body = {}) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
      keepalive: true,
    }).catch(() => null);
  }

  async function sendSpaceStop() {
    const now = Date.now();
    if (now - lastStopAt < STOP_COOLDOWN_MS) return;
    lastStopAt = now;
    const detail = { reason: 'space-global-stop', path: window.location.pathname };
    window.dispatchEvent(new CustomEvent('pisd:space-stop', { detail }));
    if (window.location.pathname === '/ai-mode') {
      await postJson('/api/ai/stop', detail);
    }
    await postJson('/api/control/stop', detail);
  }

  document.addEventListener('keydown', (event) => {
    if (shouldIgnoreSpace(event)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!event.repeat) sendSpaceStop();
  }, { capture: true, passive: false });

  window.PiSDGlobalSpaceStop = { sendSpaceStop };
})();
