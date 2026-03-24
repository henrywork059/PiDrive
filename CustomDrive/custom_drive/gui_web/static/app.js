(() => {
  const styleSettingsFields = [
    { id: 'styleAccent', cssVar: '--accent', type: 'color', fallback: '#f4a31e' },
    { id: 'stylePanel', cssVar: '--panel', type: 'color', fallback: '#232630' },
    { id: 'stylePanelAlt', cssVar: '--panel-alt', type: 'color', fallback: '#2a2e39' },
    { id: 'styleText', cssVar: '--text', type: 'color', fallback: '#f1f2f7' },
    { id: 'styleMuted', cssVar: '--muted', type: 'color', fallback: '#9ea5b5' },
    { id: 'styleFontScale', cssVar: '--font-scale', type: 'range', unit: '%', fallback: 80 },
    { id: 'styleWorkspacePad', cssVar: '--workspace-pad', type: 'range', unit: 'px', fallback: 10 },
    { id: 'styleGap', cssVar: '--gap', type: 'range', unit: 'px', fallback: 4 },
    { id: 'styleRadius', cssVar: '--radius', type: 'range', unit: 'px', fallback: 10 },
    { id: 'stylePanelPad', cssVar: '--panel-pad', type: 'range', unit: 'px', fallback: 12 },
    { id: 'styleHeaderPadY', cssVar: '--panel-head-pad-y', type: 'range', unit: 'px', fallback: 8 },
    { id: 'styleCardGap', cssVar: '--card-gap', type: 'range', unit: 'px', fallback: 10 },
    { id: 'styleFieldGap', cssVar: '--field-gap', type: 'range', unit: 'px', fallback: 10 },
  ];

  const state = {
    previewEnabled: true,
    pointerActive: false,
    rawTargetSteering: 0,
    rawTargetThrottle: 0,
    targetSteering: 0,
    targetThrottle: 0,
    manualSteering: 0,
    manualThrottle: 0,
    lastSentSteering: 0,
    lastSentThrottle: 0,
    lastControlSentAt: 0,
    estopEnabled: false,
    maxThrottle: 0.55,
    steerMix: 0.5,
    steerBias: 0.0,
    controlTimer: null,
    statusTimer: null,
  };

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, Number(value || 0)));
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setBanner(message, tone = 'muted') {
    const el = document.getElementById('statusBanner');
    if (!el) return;
    el.className = `banner ${tone}`;
    el.textContent = message;
  }

  function normalizeHexColor(value, fallback = '#000000') {
    const raw = String(value || '').trim();
    const short = raw.match(/^#([0-9a-f]{3})$/i);
    if (short) return `#${short[1].split('').map((part) => part + part).join('')}`.toLowerCase();
    const full = raw.match(/^#([0-9a-f]{6})$/i);
    if (full) return `#${full[1]}`.toLowerCase();
    return fallback;
  }

  function hexToRgbTriplet(value) {
    const hex = normalizeHexColor(value, '#000000').slice(1);
    return [0, 2, 4].map((start) => parseInt(hex.slice(start, start + 2), 16)).join(', ');
  }

  function parseNumericStyleValue(value, fallback = 0) {
    const match = String(value || '').match(/-?\d+(?:\.\d+)?/);
    return match ? Number(match[0]) : fallback;
  }

  function styleManager() {
    return window.PiServerStyle || null;
  }

  function readResolvedStyleVars() {
    return styleManager()?.getResolvedVars?.() || {};
  }

  function collectStyleOverridesFromInputs() {
    const overrides = {};
    styleSettingsFields.forEach((field) => {
      const el = document.getElementById(field.id);
      if (!el) return;
      const value = field.type === 'range'
        ? `${el.value}${field.unit || ''}`
        : normalizeHexColor(el.value, field.fallback);
      overrides[field.cssVar] = value;
      if (field.cssVar === '--accent') overrides['--accent-rgb'] = hexToRgbTriplet(value);
      if (field.cssVar === '--font-scale') overrides['--font-scale-factor'] = String(Number(el.value) / 100);
    });
    return overrides;
  }

  function syncStyleValueLabelsFromInputs() {
    styleSettingsFields.forEach((field) => {
      if (field.type !== 'range') return;
      const el = document.getElementById(field.id);
      const valueEl = document.getElementById(`${field.id}Value`);
      if (el && valueEl) valueEl.textContent = `${el.value}${field.unit || ''}`;
    });
  }

  function syncDriveValueLabels() {
    setText('maxThrottleValue', state.maxThrottle.toFixed(2));
    setText('steerMixValue', state.steerMix.toFixed(2));
    setText('steerBiasValue', state.steerBias.toFixed(2));
  }

  function syncStyleInputsFromCurrentVars() {
    const resolved = readResolvedStyleVars();
    styleSettingsFields.forEach((field) => {
      const el = document.getElementById(field.id);
      if (!el) return;
      const raw = resolved[field.cssVar];
      if (field.type === 'range') {
        el.value = String(parseNumericStyleValue(raw, field.fallback || 0));
      } else {
        el.value = normalizeHexColor(raw, field.fallback);
      }
    });
    syncStyleValueLabelsFromInputs();
  }

  function previewStyleOverridesFromInputs() {
    const manager = styleManager();
    manager?.applyTheme?.(manager.getCurrentTheme?.());
    const root = document.documentElement;
    Object.entries(collectStyleOverridesFromInputs()).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    syncStyleValueLabelsFromInputs();
  }

  function openSettings() {
    const modal = document.getElementById('settingsModal');
    if (!modal) return;
    syncStyleInputsFromCurrentVars();
    syncDriveValueLabels();
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeSettings() {
    const modal = document.getElementById('settingsModal');
    if (!modal) return;
    const manager = styleManager();
    manager?.applyTheme?.(manager.getCurrentTheme?.());
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function saveStyleSettings() {
    const overrides = collectStyleOverridesFromInputs();
    styleManager()?.saveCustomOverrides?.(overrides);
    setBanner('Style settings saved.', 'muted');
  }

  function resetStyleSettings() {
    styleManager()?.resetCustomOverrides?.();
    syncStyleInputsFromCurrentVars();
  }

  function updateToggleButton() {
    const btn = document.getElementById('previewToggleBtn');
    if (!btn) return;
    btn.setAttribute('aria-pressed', state.previewEnabled ? 'true' : 'false');
    btn.textContent = state.previewEnabled ? 'Preview ON' : 'Preview OFF';
  }

  function updateEstopButton() {
    const btn = document.getElementById('estopBtn');
    if (!btn) return;
    btn.setAttribute('aria-pressed', state.estopEnabled ? 'true' : 'false');
    btn.textContent = state.estopEnabled ? 'E-stop ON' : 'E-stop OFF';
    btn.classList.toggle('active', state.estopEnabled);
  }

  function refreshManualReadout() {
    const throttleRatio = state.maxThrottle > 0 ? clamp(state.manualThrottle / state.maxThrottle, -1, 1) : 0;
    const dot = document.getElementById('joystickDot');
    if (dot) {
      dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
      dot.style.top = `${(0.5 - throttleRatio * 0.5) * 100}%`;
    }
    setText(
      'joystickText',
      `Steering ${state.manualSteering.toFixed(2)} · Throttle ${state.manualThrottle.toFixed(2)} · Target ${state.targetSteering.toFixed(2)} / ${state.targetThrottle.toFixed(2)}`
    );
    setText('metricTarget', `S ${state.targetSteering.toFixed(2)} · T ${state.targetThrottle.toFixed(2)}`);
    syncDriveValueLabels();
  }

  function setManualTargets(steering, throttle) {
    state.rawTargetSteering = clamp(steering, -1, 1);
    state.rawTargetThrottle = clamp(throttle, -1, 1);
    state.targetSteering = state.rawTargetSteering;
    state.targetThrottle = clamp(state.rawTargetThrottle * state.maxThrottle, -state.maxThrottle, state.maxThrottle);
    refreshManualReadout();
  }

  function syncVideoFeedSource() {
    const img = document.getElementById('videoFeed');
    if (!img) return;
    if (state.previewEnabled) {
      img.src = `/video_feed?t=${Date.now()}`;
    } else {
      img.removeAttribute('src');
    }
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.message || `HTTP ${response.status}`);
    }
    return data;
  }

  async function sendControlUpdate(force = false) {
    const now = Date.now();
    const changed = Math.abs(state.manualSteering - state.lastSentSteering) > 0.01
      || Math.abs(state.manualThrottle - state.lastSentThrottle) > 0.01
      || force;
    if (!force && !changed && now - state.lastControlSentAt < 250) return;
    state.lastSentSteering = state.manualSteering;
    state.lastSentThrottle = state.manualThrottle;
    state.lastControlSentAt = now;
    try {
      await postJson('/api/control', {
        steering: state.manualSteering,
        throttle: state.manualThrottle,
        max_throttle: state.maxThrottle,
        steer_mix: state.steerMix,
        steer_bias: state.steerBias,
      });
    } catch (error) {
      setBanner(`Failed to send drive control: ${error}`, 'danger');
    }
  }

  async function fetchStatus() {
    try {
      const response = await fetch('/api/status', { cache: 'no-store' });
      const payload = await response.json();
      const camera = payload.camera || {};
      const motor = payload.motor || {};
      const runtime = payload.state || {};
      state.previewEnabled = Boolean(camera.preview_enabled);
      state.estopEnabled = Boolean(runtime.safety_stop);
      state.maxThrottle = clamp(runtime.max_throttle ?? state.maxThrottle, 0.1, 1.0);
      state.steerMix = clamp(runtime.steer_mix ?? state.steerMix, 0.0, 1.0);
      state.steerBias = clamp(runtime.steer_bias ?? state.steerBias, -0.5, 0.5);
      const maxThrottleInput = document.getElementById('maxThrottleInput');
      const steerMixInput = document.getElementById('steerMixInput');
      const steerBiasInput = document.getElementById('steerBiasInput');
      if (maxThrottleInput) maxThrottleInput.value = state.maxThrottle.toFixed(2);
      if (steerMixInput) steerMixInput.value = state.steerMix.toFixed(2);
      if (steerBiasInput) steerBiasInput.value = state.steerBias.toFixed(2);
      syncDriveValueLabels();
      setText('metricDrive', state.estopEnabled ? 'E-stop' : 'manual');
      setText('metricApplied', `S ${Number(runtime.applied_steering || 0).toFixed(2)} · T ${Number(runtime.applied_throttle || 0).toFixed(2)}`);
      setText('metricMotor', `L ${Number(runtime.motor_left || 0).toFixed(2)} · R ${Number(runtime.motor_right || 0).toFixed(2)}`);
      setText('metricCamera', camera.preview_live ? 'live' : 'waiting');
      setText('metricFps', Number(camera.fps || 0).toFixed(1));
      setText('metricResolution', `${camera.width || 0} × ${camera.height || 0}`);
      setText('metricBackend', camera.backend || 'unknown');
      setText('metricPreview', camera.preview_enabled ? 'enabled' : 'disabled');
      setText('metricError', camera.last_error || 'none');
      setText('metricAlgorithm', runtime.active_algorithm || 'manual');
      setText('metricGpio', motor.gpio_available ? 'real GPIO' : 'sim');
      setText('metricPreviewLive', camera.preview_live ? 'yes' : 'no');
      const updated = new Date((payload.timestamp || Date.now() / 1000) * 1000);
      setText('metricUpdated', updated.toLocaleTimeString());
      setText('cameraPreviewMeta', camera.preview_live
        ? `Live camera · ${camera.backend || 'unknown'} · ${camera.width || 0} × ${camera.height || 0}`
        : `Waiting for live camera · ${camera.backend || 'unknown'}`);
      setText('systemNote', motor.gpio_available
        ? 'This GUI is sending real manual motor commands through PiServer ControlService.'
        : 'GPIO is not available here, so motor output is in simulation mode.');
      setBanner(payload.message || 'Ready', camera.last_error ? 'danger' : 'muted');
      updateToggleButton();
      updateEstopButton();
    } catch (error) {
      setBanner(`Failed to read GUI status: ${error}`, 'danger');
      setText('metricError', String(error));
    }
  }

  async function togglePreview() {
    const next = !state.previewEnabled;
    try {
      const payload = await postJson('/api/camera/preview_state', { enabled: next });
      state.previewEnabled = Boolean(payload.enabled);
      updateToggleButton();
      syncVideoFeedSource();
      await fetchStatus();
    } catch (error) {
      setBanner(`Failed to change preview state: ${error}`, 'danger');
    }
  }

  async function toggleEstop() {
    try {
      const payload = await postJson('/api/safety_stop', { enabled: !state.estopEnabled });
      state.estopEnabled = Boolean(payload.enabled);
      if (state.estopEnabled) {
        state.manualSteering = 0;
        state.manualThrottle = 0;
        setManualTargets(0, 0);
      }
      updateEstopButton();
      await fetchStatus();
    } catch (error) {
      setBanner(`Failed to change E-stop: ${error}`, 'danger');
    }
  }

  async function saveRuntime() {
    try {
      await postJson('/api/runtime/save', {});
      await fetchStatus();
      setBanner('Drive settings saved.', 'muted');
    } catch (error) {
      setBanner(`Failed to save drive settings: ${error}`, 'danger');
    }
  }

  function updatePointerTarget(clientX, clientY) {
    const area = document.getElementById('joystickArea');
    if (!area) return;
    const rect = area.getBoundingClientRect();
    const nx = clamp((clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
    const ny = clamp((clientY - rect.top) / Math.max(rect.height, 1), 0, 1);
    const steering = (nx - 0.5) * 2;
    const throttle = (0.5 - ny) * 2;
    setManualTargets(steering, throttle);
  }

  function attachJoystickHandlers() {
    const area = document.getElementById('joystickArea');
    if (!area) return;

    area.addEventListener('pointerdown', (event) => {
      state.pointerActive = true;
      area.setPointerCapture(event.pointerId);
      updatePointerTarget(event.clientX, event.clientY);
      event.preventDefault();
    });

    area.addEventListener('pointermove', (event) => {
      if (!state.pointerActive) return;
      updatePointerTarget(event.clientX, event.clientY);
      event.preventDefault();
    });

    const endPointer = () => {
      state.pointerActive = false;
      setManualTargets(0, 0);
    };

    area.addEventListener('pointerup', endPointer);
    area.addEventListener('pointercancel', endPointer);
    area.addEventListener('lostpointercapture', endPointer);
  }

  function controlLoopTick() {
    const steerStep = 0.12;
    const throttleStep = Math.max(0.04, state.maxThrottle / 8);
    const nextSteer = state.manualSteering + clamp(state.targetSteering - state.manualSteering, -steerStep, steerStep);
    const nextThrottle = state.manualThrottle + clamp(state.targetThrottle - state.manualThrottle, -throttleStep, throttleStep);
    const steerChanged = Math.abs(nextSteer - state.manualSteering) > 0.0001;
    const throttleChanged = Math.abs(nextThrottle - state.manualThrottle) > 0.0001;
    if (!steerChanged && !throttleChanged) return;
    state.manualSteering = clamp(nextSteer, -1, 1);
    state.manualThrottle = clamp(nextThrottle, -state.maxThrottle, state.maxThrottle);
    refreshManualReadout();
    sendControlUpdate(false);
  }

  function bindControls() {
    document.getElementById('previewToggleBtn')?.addEventListener('click', togglePreview);
    document.getElementById('estopBtn')?.addEventListener('click', toggleEstop);
    document.getElementById('saveRuntimeBtn')?.addEventListener('click', saveRuntime);
    document.getElementById('centerPadBtn')?.addEventListener('click', () => {
      setManualTargets(0, 0);
      sendControlUpdate(true);
    });
    document.getElementById('stopDriveBtn')?.addEventListener('click', () => {
      state.manualSteering = 0;
      state.manualThrottle = 0;
      setManualTargets(0, 0);
      sendControlUpdate(true);
    });

    const maxThrottleInput = document.getElementById('maxThrottleInput');
    const steerMixInput = document.getElementById('steerMixInput');
    const steerBiasInput = document.getElementById('steerBiasInput');
    maxThrottleInput?.addEventListener('input', () => {
      state.maxThrottle = clamp(maxThrottleInput.value, 0.1, 1.0);
      setManualTargets(state.rawTargetSteering, state.rawTargetThrottle);
      syncDriveValueLabels();
    });
    steerMixInput?.addEventListener('input', () => {
      state.steerMix = clamp(steerMixInput.value, 0.0, 1.0);
      syncDriveValueLabels();
    });
    steerBiasInput?.addEventListener('input', () => {
      state.steerBias = clamp(steerBiasInput.value, -0.5, 0.5);
      syncDriveValueLabels();
    });

    document.getElementById('openSettingsBtn')?.addEventListener('click', openSettings);
    document.getElementById('closeSettingsBtn')?.addEventListener('click', closeSettings);
    document.getElementById('saveSettingsBtn')?.addEventListener('click', saveStyleSettings);
    document.getElementById('resetStyleSettingsBtn')?.addEventListener('click', resetStyleSettings);
    document.querySelectorAll('[data-close-settings-modal="true"]').forEach((el) => {
      el.addEventListener('click', closeSettings);
    });
    styleSettingsFields.forEach((field) => {
      document.getElementById(field.id)?.addEventListener('input', previewStyleOverridesFromInputs);
    });

    const videoFeed = document.getElementById('videoFeed');
    videoFeed?.addEventListener('error', () => {
      setBanner('Live preview could not be loaded.', 'danger');
      setText('cameraPreviewMeta', 'Live preview could not be loaded. Check CameraService or refresh the page.');
    });
  }

  function startLoops() {
    fetchStatus();
    state.statusTimer = window.setInterval(fetchStatus, 1000);
    state.controlTimer = window.setInterval(controlLoopTick, 60);
  }

  syncStyleInputsFromCurrentVars();
  syncDriveValueLabels();
  updateToggleButton();
  updateEstopButton();
  refreshManualReadout();
  syncVideoFeedSource();
  attachJoystickHandlers();
  bindControls();
  startLoops();
})();
