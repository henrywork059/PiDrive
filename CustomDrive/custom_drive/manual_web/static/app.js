const state = {
  page: 'manual',
  manualSteering: 0,
  manualThrottle: 0,
  maxThrottle: 0.55,
  steerMix: 0.5,
  refreshMs: 200,
  latestStatus: null,
  previewTimer: null,
  statusTimer: null,
  previewInFlight: false,
  previewObjectUrl: null,
  showCamera: true,
  keyState: { up: false, down: false, left: false, right: false },
  controlTimer: null,
  controlInFlight: false,
  pendingControl: false,
  controlIntervalMs: 80,
  manualConfig: null,
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : {};
  if (!response.ok) {
    throw new Error(data.message || data.error || `Request failed (${response.status})`);
  }
  return data;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function fmt(value, digits = 2) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : '0.00';
}

function setBanner(id, text, tone = 'muted') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `banner ${tone}${el.classList.contains('compact-banner') ? ' compact-banner' : ''}`;
}

function updateRangeText() {
  document.getElementById('manualSpeedValue').textContent = fmt(state.maxThrottle);
  document.getElementById('steerMixValue').textContent = fmt(state.steerMix);
}

function syncSliderInputs() {
  const speed = document.getElementById('manualSpeed');
  const steer = document.getElementById('steerMix');
  if (speed) speed.value = Math.round(state.maxThrottle * 100);
  if (steer) steer.value = Math.round(state.steerMix * 100);
  updateRangeText();
}

function populateManualConfig(config) {
  if (!config) return;
  state.manualConfig = config;
  const ui = config.ui || {};
  const server = config.server || {};
  const nextSpeed = Number(ui.manual_speed ?? state.maxThrottle);
  const nextRefresh = Number(server.refresh_ms ?? state.refreshMs);
  const refreshChanged = nextRefresh !== state.refreshMs;
  state.maxThrottle = clamp(nextSpeed, 0.05, 1.0);
  state.refreshMs = clamp(nextRefresh, 50, 5000);
  state.showCamera = Boolean(ui.show_camera ?? true);
  document.getElementById('showCameraToggle').checked = state.showCamera;
  document.getElementById('videoFeed').style.display = state.showCamera ? 'block' : 'none';
  syncSliderInputs();
  if (refreshChanged) restartPolling();
}

function collectManualConfig() {
  const config = JSON.parse(JSON.stringify(state.manualConfig || {}));
  config.ui = config.ui || {};
  config.server = config.server || {};
  config.ui.manual_speed = Number(document.getElementById('manualSpeed').value || 55) / 100;
  config.ui.show_camera = document.getElementById('showCameraToggle').checked;
  return config;
}

async function sendControlNow(extra = {}) {
  const payload = {
    steering: state.manualSteering,
    throttle: state.manualThrottle,
    max_throttle: state.maxThrottle,
    steer_mix: state.steerMix,
    current_page: state.page,
    algorithm: 'manual',
    ...extra,
  };
  const data = await fetchJson('/api/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (data && data.state) {
    updateStatusUi(data.state);
  }
}

function queueControlUpdate(extra = {}) {
  state.pendingControl = true;
  if (state.controlTimer) return;
  state.controlTimer = setTimeout(async () => {
    state.controlTimer = null;
    if (state.controlInFlight) {
      queueControlUpdate(extra);
      return;
    }
    if (!state.pendingControl) return;
    state.pendingControl = false;
    state.controlInFlight = true;
    try {
      await sendControlNow(extra);
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    } finally {
      state.controlInFlight = false;
      if (state.pendingControl) queueControlUpdate();
    }
  }, state.controlIntervalMs);
}

function updateArmUi(armStatus = {}) {
  const badge = document.getElementById('armStateBadge');
  const metric = document.getElementById('metricArm');
  const available = Boolean(armStatus.available);
  const enabled = Boolean(armStatus.enabled);
  const text = !enabled ? 'disabled' : available ? `ready · ${armStatus.backend || 'arm'}` : 'error';
  badge.textContent = enabled ? (available ? 'arm ready' : 'arm error') : 'arm off';
  badge.classList.toggle('off', !(enabled && available));
  metric.textContent = text;
  setBanner('armMessage', armStatus.last_message || 'Arm ready when enabled in manual_control.json.', armStatus.last_error ? 'warn' : 'muted');
}

function updateStatusUi(status) {
  state.latestStatus = status;
  document.getElementById('metricAlgorithm').textContent = status.active_algorithm || 'manual';
  document.getElementById('metricFps').textContent = fmt(status.fps, 1);
  document.getElementById('metricRec').textContent = status.recording ? 'on' : 'off';
  document.getElementById('metricWheels').textContent = `${fmt(status.motor_left)} / ${fmt(status.motor_right)}`;
  document.getElementById('metricCamera').textContent = `${status.camera_backend || 'unknown'} ${status.camera_width || 0}×${status.camera_height || 0}`;
  document.getElementById('metricGpio').textContent = String(Boolean((status.motor_config || {}).gpio_available));
  document.getElementById('recordStateBadge').textContent = status.recording ? 'record on' : 'record off';
  document.getElementById('recordStateBadge').classList.toggle('off', !status.recording);
  document.getElementById('estopStateBadge').textContent = status.safety_stop ? 'e-stop on' : 'e-stop clear';
  document.getElementById('estopStateBadge').classList.toggle('off', !status.safety_stop);
  document.getElementById('runtimeConfigPath').textContent = status.runtime_config_path || 'PiServer/config/runtime.json';
  document.getElementById('cameraPreviewMeta').textContent = status.camera_preview_live
    ? `Live preview ready · ${fmt(status.fps, 1)} FPS`
    : `Preview idle/warming up · backend ${status.camera_backend || 'unknown'}`;
  setBanner('statusBanner', status.system_message || 'Ready.', status.safety_stop ? 'warn' : 'muted');
  document.getElementById('statusDump').textContent = JSON.stringify({
    steering: status.applied_steering,
    throttle: status.applied_throttle,
    max_throttle: status.max_throttle,
    steer_mix: status.steer_mix,
    recorder_sessions: status.recorder_sessions || [],
    camera_error: status.camera_error || '',
    arm_status: status.arm_status || {},
  }, null, 2);
  if (typeof status.max_throttle === 'number') {
    state.maxThrottle = clamp(Number(status.max_throttle), 0, 1);
  }
  if (typeof status.steer_mix === 'number') {
    state.steerMix = clamp(Number(status.steer_mix), 0, 1);
  }
  syncSliderInputs();
  updateArmUi(status.arm_status || {});
}

function updateJoystickUi() {
  const dot = document.getElementById('joystickDot');
  const text = document.getElementById('joystickText');
  dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
  dot.style.top = `${(0.5 - state.manualThrottle / 2.0 / Math.max(state.maxThrottle || 1, 0.01)) * 100}%`;
  dot.style.transform = 'translate(-50%, -50%)';
  text.textContent = `Steering ${fmt(state.manualSteering)} · Throttle ${fmt(state.manualThrottle)}`;
}

function applyManualState() {
  updateJoystickUi();
  queueControlUpdate();
}

function resetManualState(send = true) {
  state.manualSteering = 0;
  state.manualThrottle = 0;
  updateJoystickUi();
  if (send) queueControlUpdate();
}

function updateFromKeyboard() {
  const turn = (state.keyState.right ? 1 : 0) - (state.keyState.left ? 1 : 0);
  const throttle = (state.keyState.up ? 1 : 0) - (state.keyState.down ? 1 : 0);
  state.manualSteering = clamp(turn, -1, 1);
  state.manualThrottle = clamp(throttle * state.maxThrottle, -1, 1);
  applyManualState();
}

function setupJoystick() {
  const area = document.getElementById('joystickArea');

  function moveDot(clientX, clientY) {
    const rect = area.getBoundingClientRect();
    const x = clamp((clientX - rect.left) / rect.width, 0, 1);
    const y = clamp((clientY - rect.top) / rect.height, 0, 1);
    state.manualSteering = clamp((x - 0.5) * 2, -1, 1);
    state.manualThrottle = clamp((0.5 - y) * 2 * state.maxThrottle, -1, 1);
    applyManualState();
  }

  function handleKeyChange(event, pressed) {
    const tag = event.target && event.target.tagName ? event.target.tagName.toLowerCase() : '';
    if (['input', 'select', 'textarea', 'button'].includes(tag)) return;
    const key = String(event.key || '').toLowerCase();
    let handled = true;
    if (key === 'w' || key === 'arrowup') state.keyState.up = pressed;
    else if (key === 's' || key === 'arrowdown') state.keyState.down = pressed;
    else if (key === 'a' || key === 'arrowleft') state.keyState.left = pressed;
    else if (key === 'd' || key === 'arrowright') state.keyState.right = pressed;
    else handled = false;
    if (handled) {
      event.preventDefault();
      updateFromKeyboard();
    }
  }

  area.addEventListener('pointerdown', (event) => {
    area.setPointerCapture(event.pointerId);
    moveDot(event.clientX, event.clientY);
  });
  area.addEventListener('pointermove', (event) => {
    if (event.buttons) moveDot(event.clientX, event.clientY);
  });
  area.addEventListener('pointerup', () => resetManualState(true));
  area.addEventListener('pointerleave', () => resetManualState(true));

  window.addEventListener('keydown', (event) => handleKeyChange(event, true));
  window.addEventListener('keyup', (event) => handleKeyChange(event, false));
}

function bindHoldButton(id, steering, throttle) {
  const btn = document.getElementById(id);
  const apply = () => {
    state.manualSteering = steering;
    state.manualThrottle = throttle * state.maxThrottle;
    applyManualState();
  };
  const release = () => resetManualState(true);
  btn.addEventListener('pointerdown', apply);
  btn.addEventListener('pointerup', release);
  btn.addEventListener('pointerleave', release);
  btn.addEventListener('touchstart', (event) => { event.preventDefault(); apply(); }, { passive: false });
  btn.addEventListener('touchend', release);
}

async function pollStatus() {
  try {
    const data = await fetchJson('/api/status');
    updateStatusUi(data);
    if (!state.manualConfig && data.manual_config) {
      populateManualConfig(data.manual_config);
    }
  } catch (error) {
    setBanner('systemMessage', error.message, 'warn');
  }
}

async function pollPreview() {
  if (!state.showCamera || state.previewInFlight) return;
  state.previewInFlight = true;
  try {
    const response = await fetch(`/api/camera/frame.jpg?ts=${Date.now()}`, { cache: 'no-store' });
    if (response.status === 204) return;
    if (!response.ok) throw new Error(`Preview failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const img = document.getElementById('videoFeed');
    img.src = url;
    if (state.previewObjectUrl) URL.revokeObjectURL(state.previewObjectUrl);
    state.previewObjectUrl = url;
  } catch (error) {
    setBanner('systemMessage', error.message, 'warn');
  } finally {
    state.previewInFlight = false;
  }
}

function restartPolling() {
  if (state.statusTimer) clearInterval(state.statusTimer);
  if (state.previewTimer) clearInterval(state.previewTimer);
  state.statusTimer = setInterval(pollStatus, state.refreshMs);
  state.previewTimer = setInterval(pollPreview, Math.max(120, state.refreshMs));
}

async function togglePreview(enabled) {
  state.showCamera = Boolean(enabled);
  document.getElementById('videoFeed').style.display = state.showCamera ? 'block' : 'none';
  try {
    const data = await fetchJson('/api/camera/preview_state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: state.showCamera }),
    });
    if (data.state) updateStatusUi(data.state);
  } catch (error) {
    setBanner('systemMessage', error.message, 'warn');
  }
}

async function performArmAction(action) {
  try {
    const data = await fetchJson('/api/arm/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    if (data.state) updateStatusUi(data.state);
    setBanner('armMessage', data.message || `Arm ${action} sent.`, data.ok ? 'good' : 'warn');
  } catch (error) {
    setBanner('armMessage', error.message, 'warn');
  }
}

function setupButtons() {
  bindHoldButton('forwardBtn', 0, 1);
  bindHoldButton('reverseBtn', 0, -1);
  bindHoldButton('leftBtn', -1, 0);
  bindHoldButton('rightBtn', 1, 0);

  document.getElementById('stopBtn').addEventListener('click', () => {
    resetManualState(true);
    setBanner('manualMessage', 'Manual stop sent.', 'muted');
  });

  document.getElementById('recordToggleBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/record/toggle', { method: 'POST' });
      updateStatusUi(data.state || state.latestStatus || {});
      setBanner('manualMessage', data.message || 'Recording toggled.', 'muted');
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('estopBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/system/estop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: true }),
      });
      if (data.state) updateStatusUi(data.state);
      resetManualState(false);
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('clearEstopBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/system/estop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: false }),
      });
      if (data.state) updateStatusUi(data.state);
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('saveRuntimeBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/config/save', { method: 'POST' });
      if (data.state) updateStatusUi(data.state);
      setBanner('systemMessage', data.message || 'Runtime saved.', 'good');
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });

  document.getElementById('reloadRuntimeBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/config/reload', { method: 'POST' });
      if (data.state) updateStatusUi(data.state);
      setBanner('systemMessage', data.message || 'Runtime reloaded.', 'good');
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });

  document.getElementById('saveUiBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/manual/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(collectManualConfig()),
      });
      if (data.config) populateManualConfig(data.config);
      if (data.state) updateStatusUi(data.state);
      setBanner('systemMessage', data.message || 'Panel settings saved.', 'good');
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });

  document.getElementById('reloadUiBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/manual/config');
      populateManualConfig(data.config);
      await togglePreview(document.getElementById('showCameraToggle').checked);
      setBanner('systemMessage', 'Panel settings reloaded.', 'good');
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });

  document.getElementById('showCameraToggle').addEventListener('change', async (event) => {
    await togglePreview(event.target.checked);
  });

  document.getElementById('manualSpeed').addEventListener('input', (event) => {
    state.maxThrottle = clamp(Number(event.target.value || 55) / 100, 0.05, 1.0);
    updateRangeText();
    queueControlUpdate();
  });

  document.getElementById('steerMix').addEventListener('input', (event) => {
    state.steerMix = clamp(Number(event.target.value || 50) / 100, 0.0, 1.0);
    updateRangeText();
    queueControlUpdate();
  });

  document.getElementById('armUpBtn').addEventListener('click', () => performArmAction('up'));
  document.getElementById('armDownBtn').addEventListener('click', () => performArmAction('down'));
  document.getElementById('armHoldBtn').addEventListener('click', () => performArmAction('hold'));
  document.getElementById('armReleaseBtn').addEventListener('click', () => performArmAction('release'));
}

async function boot() {
  updateJoystickUi();
  setupJoystick();
  setupButtons();
  restartPolling();
  try {
    const manualConfig = await fetchJson('/api/manual/config');
    populateManualConfig(manualConfig.config);
    await togglePreview(document.getElementById('showCameraToggle').checked);
  } catch (error) {
    setBanner('systemMessage', error.message, 'warn');
  }
  await pollStatus();
  await pollPreview();
}

document.addEventListener('DOMContentLoaded', boot);
window.addEventListener('beforeunload', () => {
  if (state.previewObjectUrl) URL.revokeObjectURL(state.previewObjectUrl);
});
