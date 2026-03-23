const state = {
  maxThrottle: 0.55,
  steerMix: 0.50,
  manualSteering: 0.0,
  manualThrottle: 0.0,
  keyState: { up: false, down: false, left: false, right: false },
  currentSession: 'session_1',
  refreshMs: 200,
};

let pollTimer = null;

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || 'Request failed');
  }
  return data;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function setBanner(id, text, tone = 'muted') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `banner ${tone}`;
}

function fmt(value, digits = 2) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : '0.00';
}

function updateRangeText() {
  document.getElementById('manualSpeedValue').textContent = state.maxThrottle.toFixed(2);
  document.getElementById('steerMixValue').textContent = state.steerMix.toFixed(2);
}

function currentSessionData(config) {
  const competition = config?.competition || {};
  const sessions = competition.sessions || {};
  const key = competition.current_session || state.currentSession || 'session_1';
  return { key, session: sessions[key] || {} };
}

function populateManualConfig(config) {
  if (!config) return;
  const ui = config.ui || {};
  const server = config.server || {};
  const nextSpeed = Number(ui.manual_speed || state.maxThrottle);
  const nextRefresh = Number(server.refresh_ms || state.refreshMs);
  const refreshChanged = nextRefresh !== state.refreshMs;
  state.maxThrottle = nextSpeed;
  state.refreshMs = nextRefresh;
  document.getElementById('manualSpeed').value = Math.round(state.maxThrottle * 100);
  document.getElementById('showCameraToggle').checked = Boolean(ui.show_camera ?? true);
  const current = currentSessionData(config);
  state.currentSession = current.key;
  document.getElementById('sessionSelect').value = current.key;
  document.getElementById('currentSessionBadge').textContent = current.key.replace('_', ' ');
  document.getElementById('sessionLabel').value = current.session.label || '';
  document.getElementById('teamName').value = current.session.team_name || '';
  document.getElementById('driverName').value = current.session.driver_name || '';
  document.getElementById('sessionNotes').value = current.session.notes || '';
  updateRangeText();
  if (refreshChanged) restartPolling();
}

function collectSessionForm(baseConfig) {
  const config = JSON.parse(JSON.stringify(baseConfig || {}));
  config.ui = config.ui || {};
  config.server = config.server || {};
  config.competition = config.competition || {};
  config.competition.sessions = config.competition.sessions || {};
  const sessionKey = document.getElementById('sessionSelect').value || 'session_1';
  config.competition.current_session = sessionKey;
  config.ui.manual_speed = Number(document.getElementById('manualSpeed').value || 55) / 100;
  config.ui.show_camera = document.getElementById('showCameraToggle').checked;
  config.competition.sessions[sessionKey] = {
    label: document.getElementById('sessionLabel').value || (sessionKey === 'session_1' ? 'Competition Session 1' : 'Competition Session 2'),
    team_name: document.getElementById('teamName').value || '',
    driver_name: document.getElementById('driverName').value || '',
    notes: document.getElementById('sessionNotes').value || '',
  };
  return config;
}

async function sendControlUpdate(extra = {}) {
  const payload = {
    steering: state.manualSteering,
    throttle: state.manualThrottle,
    max_throttle: state.maxThrottle,
    steer_mix: state.steerMix,
    ...extra,
  };
  return fetchJson('/api/control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

function updateStatusUi(status) {
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
  const session = currentSessionData(status.manual_config || {});
  document.getElementById('currentSessionBadge').textContent = session.key.replace('_', ' ');
  const summary = `${session.session.label || ''}${session.session.team_name ? ` · Team: ${session.session.team_name}` : ''}${session.session.driver_name ? ` · Driver: ${session.session.driver_name}` : ''}`;
  document.getElementById('sessionSummary').textContent = summary;
  document.getElementById('cameraPreviewMeta').textContent = status.camera_preview_live
    ? `Live preview ready · ${fmt(status.fps, 1)} FPS`
    : `Preview placeholder or warming up · backend ${status.camera_backend || 'unknown'}`;
  setBanner('statusBanner', status.system_message || 'Ready.', status.safety_stop ? 'warn' : 'muted');
  document.getElementById('statusDump').textContent = JSON.stringify({
    steering: status.applied_steering,
    throttle: status.applied_throttle,
    max_throttle: status.max_throttle,
    steer_mix: status.steer_mix,
    recorder_sessions: status.recorder_sessions || [],
    camera_error: status.camera_error || '',
  }, null, 2);
}

function applyManualState() {
  const dot = document.getElementById('joystickDot');
  const text = document.getElementById('joystickText');
  dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
  dot.style.top = `${(0.5 - state.manualThrottle / 2.0 / Math.max(state.maxThrottle || 1, 0.01)) * 100}%`;
  dot.style.transform = 'translate(-50%, -50%)';
  text.textContent = `Steering ${state.manualSteering.toFixed(2)} · Throttle ${state.manualThrottle.toFixed(2)}`;
  sendControlUpdate().catch((error) => setBanner('manualMessage', error.message, 'warn'));
}

function resetManualState() {
  state.manualSteering = 0;
  state.manualThrottle = 0;
  applyManualState();
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
    state.manualSteering = clamp((x - 0.5) * 2.0, -1, 1);
    state.manualThrottle = clamp((0.5 - y) * 2.0 * state.maxThrottle, -1, 1);
    applyManualState();
  }

  function handleKeyChange(event, pressed) {
    const tag = (event.target && event.target.tagName) ? event.target.tagName.toLowerCase() : '';
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
  area.addEventListener('pointerup', resetManualState);
  area.addEventListener('pointercancel', resetManualState);

  window.addEventListener('keydown', (event) => handleKeyChange(event, true));
  window.addEventListener('keyup', (event) => handleKeyChange(event, false));

  document.getElementById('stopBtn').addEventListener('click', () => resetManualState());
  document.getElementById('forwardBtn').addEventListener('click', () => {
    state.manualSteering = 0;
    state.manualThrottle = state.maxThrottle;
    applyManualState();
  });
  document.getElementById('reverseBtn').addEventListener('click', () => {
    state.manualSteering = 0;
    state.manualThrottle = -state.maxThrottle;
    applyManualState();
  });
  document.getElementById('leftBtn').addEventListener('click', () => {
    state.manualSteering = -1;
    state.manualThrottle = state.maxThrottle * 0.45;
    applyManualState();
  });
  document.getElementById('rightBtn').addEventListener('click', () => {
    state.manualSteering = 1;
    state.manualThrottle = state.maxThrottle * 0.45;
    applyManualState();
  });
}

async function pollStatus() {
  try {
    const status = await fetchJson('/api/status');
    updateStatusUi(status);
  } catch (error) {
    setBanner('systemMessage', error.message, 'warn');
  }
}

function restartPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(pollStatus, clamp(state.refreshMs, 50, 5000));
}

async function loadManualConfig() {
  const data = await fetchJson('/api/manual/config');
  populateManualConfig(data.config || {});
  setBanner('sessionMessage', 'Session settings loaded.');
}

async function saveManualConfig() {
  try {
    const existing = await fetchJson('/api/manual/config');
    const payload = collectSessionForm(existing.config || {});
    const data = await fetchJson('/api/manual/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    populateManualConfig(data.config || payload);
    setBanner('sessionMessage', data.message || 'Session settings saved.');
    await pollStatus();
  } catch (error) {
    setBanner('sessionMessage', error.message, 'warn');
  }
}

function setupEvents() {
  document.getElementById('manualSpeed').addEventListener('input', async (event) => {
    state.maxThrottle = Number(event.target.value || 55) / 100;
    updateRangeText();
    try {
      await sendControlUpdate();
      setBanner('manualMessage', 'Manual speed updated.');
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('steerMix').addEventListener('input', async (event) => {
    state.steerMix = Number(event.target.value || 50) / 100;
    updateRangeText();
    try {
      await sendControlUpdate();
      setBanner('manualMessage', 'Steer mix updated.');
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('recordToggleBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/record/toggle', { method: 'POST' });
      setBanner('manualMessage', data.message || 'Record toggled.');
      await pollStatus();
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('estopBtn').addEventListener('click', async () => {
    try {
      await fetchJson('/api/system/estop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: true }),
      });
      resetManualState();
      setBanner('manualMessage', 'Emergency stop engaged.', 'warn');
      await pollStatus();
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('clearEstopBtn').addEventListener('click', async () => {
    try {
      await fetchJson('/api/system/estop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: false }),
      });
      setBanner('manualMessage', 'Emergency stop cleared.');
      await pollStatus();
    } catch (error) {
      setBanner('manualMessage', error.message, 'warn');
    }
  });

  document.getElementById('sessionSelect').addEventListener('change', async () => {
    try {
      const current = await fetchJson('/api/manual/config');
      current.config.competition.current_session = document.getElementById('sessionSelect').value || 'session_1';
      const saved = await fetchJson('/api/manual/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(current.config),
      });
      populateManualConfig(saved.config || current.config);
      setBanner('sessionMessage', 'Active session switched.');
      await pollStatus();
    } catch (error) {
      setBanner('sessionMessage', error.message, 'warn');
    }
  });

  document.getElementById('saveSessionBtn').addEventListener('click', saveManualConfig);
  document.getElementById('reloadSessionBtn').addEventListener('click', async () => {
    try {
      await loadManualConfig();
      await pollStatus();
    } catch (error) {
      setBanner('sessionMessage', error.message, 'warn');
    }
  });

  document.getElementById('showCameraToggle').addEventListener('change', async (event) => {
    const enabled = Boolean(event.target.checked);
    document.getElementById('videoFeed').style.display = enabled ? 'block' : 'none';
    try {
      await fetchJson('/api/camera/preview_state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      setBanner('sessionMessage', enabled ? 'Camera preview enabled.' : 'Camera preview disabled.');
    } catch (error) {
      setBanner('sessionMessage', error.message, 'warn');
    }
  });

  document.getElementById('saveRuntimeBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/config/save', { method: 'POST' });
      setBanner('systemMessage', data.message || 'Runtime saved.');
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });

  document.getElementById('reloadRuntimeBtn').addEventListener('click', async () => {
    try {
      const data = await fetchJson('/api/config/reload', { method: 'POST' });
      state.maxThrottle = Number(data.state?.max_throttle || state.maxThrottle);
      state.steerMix = Number(data.state?.steer_mix || state.steerMix);
      updateRangeText();
      setBanner('systemMessage', data.message || 'Runtime reloaded.');
      await pollStatus();
    } catch (error) {
      setBanner('systemMessage', error.message, 'warn');
    }
  });
}

async function init() {
  setupJoystick();
  setupEvents();
  await loadManualConfig();
  await pollStatus();
  restartPolling();
}

init().catch((error) => {
  setBanner('systemMessage', error.message || 'Manual control failed to initialise.', 'warn');
});
