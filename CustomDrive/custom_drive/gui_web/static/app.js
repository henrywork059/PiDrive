(() => {
  const state = {
    previewEnabled: true,
    frameTimer: null,
    statusTimer: null,
    previewObjectUrl: null,
    previewInFlight: false,
  };

  function setBanner(message, tone = 'muted') {
    const el = document.getElementById('statusBanner');
    if (!el) return;
    el.className = `banner ${tone}`;
    el.textContent = message;
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function updateToggleButton() {
    const btn = document.getElementById('previewToggleBtn');
    if (!btn) return;
    btn.setAttribute('aria-pressed', state.previewEnabled ? 'true' : 'false');
    btn.textContent = state.previewEnabled ? 'Preview ON' : 'Preview OFF';
  }

  async function fetchStatus() {
    try {
      const response = await fetch('/api/status', { cache: 'no-store' });
      const payload = await response.json();
      const camera = payload.camera || {};
      setText('metricGui', payload.gui?.title ? 'ready' : 'offline');
      setText('metricCamera', camera.live ? 'live' : 'waiting');
      setText('metricPreview', camera.preview_enabled ? 'enabled' : 'disabled');
      setText('metricBackend', camera.backend || 'unknown');
      setText('metricResolution', `${camera.width || 0} × ${camera.height || 0}`);
      setText('metricError', camera.last_error || 'none');
      setText('cameraPreviewMeta', camera.live
        ? `Live camera · ${camera.backend || 'unknown'} · ${camera.width || 0} × ${camera.height || 0}`
        : `Waiting for live camera · ${camera.backend || 'unknown'}`);
      setBanner(payload.message || 'CustomDrive GUI shell ready.', camera.last_error ? 'danger' : 'muted');
      state.previewEnabled = Boolean(camera.preview_enabled);
      updateToggleButton();
    } catch (error) {
      setText('metricGui', 'offline');
      setText('metricError', String(error));
      setBanner(`Failed to read GUI status: ${error}`, 'danger');
    }
  }

  async function refreshFrame() {
    if (!state.previewEnabled || state.previewInFlight) return;
    state.previewInFlight = true;
    try {
      const response = await fetch(`/api/camera/frame.jpg?t=${Date.now()}`, { cache: 'no-store' });
      if (response.status === 204) return;
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const nextUrl = URL.createObjectURL(blob);
      const img = document.getElementById('videoFeed');
      if (img) img.src = nextUrl;
      if (state.previewObjectUrl) URL.revokeObjectURL(state.previewObjectUrl);
      state.previewObjectUrl = nextUrl;
    } catch (error) {
      setBanner(`Preview fetch failed: ${error}`, 'danger');
    } finally {
      state.previewInFlight = false;
    }
  }

  async function togglePreview() {
    const next = !state.previewEnabled;
    try {
      const response = await fetch('/api/camera/preview_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: next }),
      });
      const payload = await response.json();
      state.previewEnabled = Boolean(payload.enabled);
      updateToggleButton();
      if (!state.previewEnabled) {
        const img = document.getElementById('videoFeed');
        if (img) img.removeAttribute('src');
      }
      await fetchStatus();
    } catch (error) {
      setBanner(`Failed to change preview state: ${error}`, 'danger');
    }
  }

  function startPolling() {
    fetchStatus();
    refreshFrame();
    state.statusTimer = window.setInterval(fetchStatus, 1000);
    state.frameTimer = window.setInterval(refreshFrame, 200);
  }

  document.getElementById('previewToggleBtn')?.addEventListener('click', togglePreview);
  updateToggleButton();
  startPolling();
})();
