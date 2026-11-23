/* R48 passive preflight panel: no POST, control command or settings mutation. */
(() => {
  'use strict';
  const root = document.querySelector('[data-preflight-root]');
  if (!root) return;
  const list = root.querySelector('[data-preflight-list]');
  const status = root.querySelector('[data-preflight-status]');
  const summary = root.querySelector('summary');
  const refresh = root.querySelector('[data-preflight-refresh]');
  if (!list || !status || !summary || !refresh) return;
  const validStates = new Set(['ready', 'attention', 'simulation', 'unknown']);
  const labels = {
    ready: 'Observed', attention: 'Needs attention',
    simulation: 'Simulation', unknown: 'Unknown',
  };
  let pending = false;

  function render(data) {
    if (data?.ok !== true || data?.read_only !== true || !Array.isArray(data.checks)) {
      throw new Error('Invalid read-only preflight response.');
    }
    const checks = data.checks.slice(0, 9);
    const rows = document.createDocumentFragment();
    let needsAttention = 0;
    let simulations = 0;
    checks.forEach((entry) => {
      const state = validStates.has(entry?.state) ? entry.state : 'unknown';
      if (state === 'attention' || state === 'unknown') needsAttention += 1;
      if (state === 'simulation') simulations += 1;
      const item = document.createElement('li');
      item.dataset.state = state;
      const label = document.createElement('strong');
      label.textContent = String(entry?.title || 'Check') + ' — ' + labels[state];
      const details = document.createElement('span');
      details.textContent = ' — ' + String(entry?.detail || 'Not available.');
      const next = document.createElement('small');
      next.textContent = ' Next: ' + String(entry?.next_step || 'Inspect the Pi.');
      item.appendChild(label);
      item.appendChild(details);
      item.appendChild(next);
      rows.appendChild(item);
    });
    list.replaceChildren(rows);
    status.textContent = checks.length + ' checks · ' + needsAttention +
      ' need attention · ' + simulations + ' simulated. No hardware actions performed.';
    summary.textContent = 'Startup preflight (read-only)' +
      (needsAttention ? ' · ' + needsAttention + ' need attention' : ' · checked');
  }

  async function loadPreflight() {
    if (pending) return;
    pending = true;
    refresh.disabled = true;
    status.textContent = 'Reading existing service status only…';
    try {
      const response = await fetch('/api/preflight', {
        method: 'GET', cache: 'no-store', credentials: 'same-origin',
      });
      if (!response.ok) throw new Error('Preflight request unavailable');
      render(await response.json());
    } catch (_error) {
      summary.textContent = 'Startup preflight (read-only) · unavailable';
      status.textContent = 'Could not read preflight. Check the Pi connection and Refresh.';
      list.replaceChildren();
    } finally {
      pending = false;
      refresh.disabled = false;
    }
  }

  refresh.addEventListener('click', loadPreflight);
  // GET on page load is observational only. The panel remains collapsed to
  // preserve the current operator layout and camera/drive control proportions.
  void loadPreflight();
})();
