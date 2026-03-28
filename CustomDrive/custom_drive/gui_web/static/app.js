const styleSettingsFields = [
  { id: 'styleBg', cssVar: '--bg', type: 'color' },
  { id: 'stylePanel', cssVar: '--panel', type: 'color' },
  { id: 'stylePanelAlt', cssVar: '--panel-alt', type: 'color' },
  { id: 'styleText', cssVar: '--text', type: 'color' },
  { id: 'styleMuted', cssVar: '--muted', type: 'color' },
  { id: 'styleAccent', cssVar: '--accent', type: 'color' },
  { id: 'styleDanger', cssVar: '--danger', type: 'color' },
  { id: 'styleWarn', cssVar: '--warn', type: 'color' },
  { id: 'styleFontScale', cssVar: '--font-scale', type: 'range', unit: '%', fallback: 80 },
  { id: 'styleWorkspacePad', cssVar: '--workspace-pad', type: 'range', unit: 'px', fallback: 10 },
  { id: 'styleGap', cssVar: '--gap', type: 'range', unit: 'px', fallback: 4 },
  { id: 'styleRadius', cssVar: '--radius', type: 'range', unit: 'px', fallback: 10 },
  { id: 'stylePanelPad', cssVar: '--panel-pad', type: 'range', unit: 'px', fallback: 12 },
  { id: 'styleHeaderPadY', cssVar: '--panel-head-pad-y', type: 'range', unit: 'px', fallback: 10 },
];

const state = {
  statusTimer: null,
  manualSteering: 0,
  manualThrottle: 0,
  maxThrottle: 0.55,
  steerMix: 0.5,
  steerBias: 0,
  previewEnabled: true,
  controlInFlight: false,
  pendingControl: false,
  lastSentSteering: 0,
  lastSentThrottle: 0,
  estopEnabled: false,
  driveSettingsLoaded: false,
  aiSettingsLoaded: false,
  aiModels: [],
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function fmt(value, digits = 2) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : '0.00';
}

function styleManager() {
  return window.PiServerStyle || null;
}

function normalizeHexColor(value, fallback = '#000000') {
  const raw = String(value || '').trim();
  const short = raw.match(/^#([0-9a-f]{3})$/i);
  if (short) return `#${short[1].split('').map((part) => part + part).join('')}`.toLowerCase();
  const full = raw.match(/^#([0-9a-f]{6})$/i);
  return full ? `#${full[1]}`.toLowerCase() : fallback;
}

function parseNumericStyleValue(value, fallback = 0) {
  const match = String(value || '').match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : fallback;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function syncEstopToggle(enabled) {
  const toggle = document.getElementById('estopToggle');
  const row = document.querySelector('.danger-toggle');
  if (toggle) toggle.checked = Boolean(enabled);
  if (row) row.classList.toggle('active', Boolean(enabled));
}

function setBanner(id, message, kind = 'muted') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message || '';
  el.className = `banner ${kind}`;
}

async function fetchJson(url, options = undefined) {
  const response = await fetch(url, options);
  let data = {};
  try { data = await response.json(); } catch {}
  if (!response.ok) {
    throw new Error(data.message || `Request failed (${response.status})`);
  }
  return data;
}

async function postJson(url, body = {}) {
  return fetchJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function getResolvedStyleVars() {
  return styleManager()?.getResolvedVars?.() || {};
}

function collectStyleOverridesFromInputs() {
  const overrides = {};
  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    const value = field.type === 'range'
      ? `${el.value}${field.unit || ''}`
      : normalizeHexColor(el.value);
    overrides[field.cssVar] = value;
    if (field.cssVar === '--accent') {
      const hex = normalizeHexColor(value, '#f4a31e').slice(1);
      overrides['--accent-rgb'] = [0, 2, 4].map((start) => parseInt(hex.slice(start, start + 2), 16)).join(', ');
    }
    if (field.cssVar === '--font-scale') overrides['--font-scale-factor'] = String(Number(el.value) / 100);
  });
  return overrides;
}

function syncStyleInputsFromCurrentVars() {
  const resolved = getResolvedStyleVars();
  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    const raw = resolved[field.cssVar];
    if (field.type === 'range') {
      const numeric = parseNumericStyleValue(raw, field.fallback || Number(el.min || 0));
      el.value = `${numeric}`;
      setText(`${field.id}Value`, `${numeric}${field.unit || ''}`);
    } else {
      el.value = normalizeHexColor(raw, el.value || '#000000');
    }
  });
}

function previewStyleOverridesFromInputs() {
  const manager = styleManager();
  manager?.applyTheme?.(manager.getCurrentTheme?.());
  const root = document.documentElement;
  Object.entries(collectStyleOverridesFromInputs()).forEach(([key, value]) => root.style.setProperty(key, value));
  styleSettingsFields.forEach((field) => {
    if (field.type === 'range') setText(`${field.id}Value`, `${document.getElementById(field.id).value}${field.unit || ''}`);
  });
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('hidden');
  modal.setAttribute('aria-hidden', 'false');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.add('hidden');
  modal.setAttribute('aria-hidden', 'true');
}

function syncManualReadout() {
  setText('joystickText', `Steering ${fmt(state.manualSteering)} · Throttle ${fmt(state.manualThrottle)}`);
  const dot = document.getElementById('joystickDot');
  if (dot) {
    dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
    const throttleRatio = state.maxThrottle > 0 ? state.manualThrottle / state.maxThrottle : 0;
    dot.style.top = `${(0.5 - throttleRatio * 0.5) * 100}%`;
  }
}

function applyDrivePadPosition(clientX, clientY) {
  const area = document.getElementById('joystickArea');
  const rect = area.getBoundingClientRect();
  const nx = clamp((clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
  const ny = clamp((clientY - rect.top) / Math.max(rect.height, 1), 0, 1);
  state.manualSteering = clamp((nx - 0.5) * 2, -1, 1);
  state.manualThrottle = clamp((0.5 - ny) * 2 * state.maxThrottle, -state.maxThrottle, state.maxThrottle);
  syncManualReadout();
  queueControlSend();
}

function releaseDrivePad() {
  state.manualSteering = 0;
  state.manualThrottle = 0;
  syncManualReadout();
  queueControlSend();
}

async function sendControlNow() {
  if (state.controlInFlight) {
    state.pendingControl = true;
    return;
  }
  const steering = clamp(state.manualSteering, -1, 1);
  const throttle = clamp(state.manualThrottle, -state.maxThrottle, state.maxThrottle);
  if (Math.abs(steering - state.lastSentSteering) < 0.01 && Math.abs(throttle - state.lastSentThrottle) < 0.01 && !state.pendingControl) {
    return;
  }
  state.controlInFlight = true;
  state.pendingControl = false;
  try {
    await postJson('/api/control', {
      steering,
      throttle,
      max_throttle: state.maxThrottle,
      steer_mix: state.steerMix,
      steer_bias: state.steerBias,
    });
    state.lastSentSteering = steering;
    state.lastSentThrottle = throttle;
  } catch (error) {
    setBanner('driveMessage', error.message || 'Manual drive failed.', 'warn');
  } finally {
    state.controlInFlight = false;
    if (state.pendingControl) {
      window.setTimeout(() => sendControlNow(), 40);
    }
  }
}

function queueControlSend() {
  window.clearTimeout(queueControlSend._timer);
  queueControlSend._timer = window.setTimeout(() => sendControlNow(), 70);
}
queueControlSend._timer = null;

function populateDriveSettings(status) {
  const motor = status.motor_config || {};
  state.maxThrottle = Number(status.max_throttle ?? state.maxThrottle ?? 0.55);
  state.steerMix = Number(status.steer_mix ?? state.steerMix ?? 0.5);
  state.steerBias = Number(status.steer_bias ?? state.steerBias ?? 0);
  document.getElementById('driveMaxThrottle').value = Math.round(state.maxThrottle * 100);
  document.getElementById('driveSteerMix').value = Math.round(state.steerMix * 100);
  document.getElementById('driveSteerBias').value = Math.round(state.steerBias * 100);
  setText('driveMaxThrottleValue', fmt(state.maxThrottle));
  setText('driveSteerMixValue', fmt(state.steerMix));
  setText('driveSteerBiasValue', fmt(state.steerBias));

  document.getElementById('leftDirection').value = String(Number(motor.left_direction ?? status.motor_left_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById('rightDirection').value = String(Number(motor.right_direction ?? status.motor_right_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById('steeringDirection').value = String(Number(motor.steering_direction ?? status.motor_steering_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById('leftMaxSpeed').value = Number(motor.left_max_speed ?? status.motor_left_max_speed ?? 1).toFixed(2);
  document.getElementById('rightMaxSpeed').value = Number(motor.right_max_speed ?? status.motor_right_max_speed ?? 1).toFixed(2);
  document.getElementById('leftBias').value = Number(motor.left_bias ?? status.motor_left_bias ?? 0).toFixed(2);
  document.getElementById('rightBias').value = Number(motor.right_bias ?? status.motor_right_bias ?? 0).toFixed(2);
  state.driveSettingsLoaded = true;
  syncManualReadout();
}

function populateAiSettings(status) {
  const ai = status.ai_status || {};
  document.getElementById('aiConfidenceThreshold').value = Number(ai.confidence_threshold ?? 0.25).toFixed(2);
  document.getElementById('aiIouThreshold').value = Number(ai.iou_threshold ?? 0.45).toFixed(2);
  document.getElementById('aiOverlayEnabled').value = ai.overlay_enabled === false ? 'false' : 'true';
  document.getElementById('aiOverlayFps').value = Number(ai.max_overlay_fps ?? 6.0).toFixed(1);
  state.aiModels = ai.models || [];
  renderAiModelOptions(ai.active_model || 'none');
  state.aiSettingsLoaded = true;
}

function renderAiModelOptions(selectedName = 'none') {
  const select = document.getElementById('aiModelSelect');
  if (!select) return;
  const models = state.aiModels || [];
  select.innerHTML = '';
  if (!models.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No models uploaded';
    select.appendChild(opt);
    return;
  }
  models.forEach((model) => {
    const opt = document.createElement('option');
    opt.value = model.name;
    const tags = [];
    if (model.has_labels) tags.push('labels');
    if (model.has_config) tags.push('config');
    if (model.active) tags.push('active');
    opt.textContent = tags.length ? `${model.name} [${tags.join(', ')}]` : model.name;
    if (model.name === selectedName) opt.selected = true;
    select.appendChild(opt);
  });
}

function updateStatusUi(data) {
  const cameraLive = Boolean(data.camera_preview_live ?? data.camera_config?.preview_enabled ?? true);
  state.previewEnabled = cameraLive;
  const previewText = cameraLive ? 'live' : 'paused';
  const driveState = data.safety_stop ? 'E-stop active' : 'Manual ready';
  const aiStatus = data.ai_status || {};
  setText('metricDriveState', driveState);
  setText('metricApplied', `S ${fmt(data.applied_steering)} · T ${fmt(data.applied_throttle)}`);
  setText('metricManual', `S ${fmt(state.manualSteering)} · T ${fmt(state.manualThrottle)}`);
  setText('metricCamera', `${data.camera_backend || 'unknown'} · ${data.camera_width || 0}×${data.camera_height || 0}`);
  setText('metricPreview', previewText);
  setText('metricArm', data.arm_status?.last_action || 'idle');
  setText('metricAi', aiStatus.ready ? (aiStatus.active_model || 'ready') : 'off');
  setText('metricMaxThrottle', fmt(data.max_throttle ?? state.maxThrottle));
  setText('metricSteerMix', fmt(data.steer_mix ?? state.steerMix));
  setText('metricSteerBias', fmt(data.steer_bias ?? state.steerBias));
  setText('metricWheels', `${fmt(data.motor_left)} / ${fmt(data.motor_right)}`);
  setText('metricFps', `${Number(data.fps || 0).toFixed(1)} FPS`);
  setText('statusMiniText', data.safety_stop ? 'estop' : 'manual');
  setText('cameraPreviewMeta', aiStatus.ready && aiStatus.overlay_enabled ? 'streaming + AI overlay' : (cameraLive ? 'streaming' : 'paused'));
  setText('systemRuntimePath', data.runtime_config_path || 'runtime.json');
  setText('systemArmLift', `${Number(data.arm_status?.lift_angle || 0).toFixed(0)}°`);
  setText('systemMotorDir', `${data.motor_left_direction ?? 1} / ${data.motor_right_direction ?? 1} / ${data.motor_steering_direction ?? 1}`);
  setBanner('statusBanner', data.system_message || 'Ready.', data.safety_stop ? 'warn' : 'muted');
  setBanner('systemMessage', data.last_error ? `Last error: ${data.last_error}` : (data.system_message || 'System ready.'), data.last_error ? 'warn' : 'muted');
  state.estopEnabled = Boolean(data.safety_stop);
  syncEstopToggle(state.estopEnabled);
  const runBadge = document.getElementById('runBadge');
  if (runBadge) {
    runBadge.textContent = data.safety_stop ? 'E-STOP' : 'MANUAL';
    runBadge.className = `badge ${data.safety_stop ? 'estop' : 'live'}`;
  }
  const armMessage = data.arm_status?.last_message || 'Arm ready.';
  setBanner('armMessage', armMessage, data.arm_status?.last_error ? 'warn' : 'muted');
  if (!state.driveSettingsLoaded) populateDriveSettings(data);
  if (!state.aiSettingsLoaded) populateAiSettings(data);
}

async function pollStatus() {
  try {
    const data = await fetchJson('/api/status');
    updateStatusUi(data);
  } catch (error) {
    setBanner('systemMessage', error.message || 'Status refresh failed.', 'warn');
  }
}

async function saveDriveSettings() {
  try {
    state.maxThrottle = clamp(Number(document.getElementById('driveMaxThrottle').value || 55) / 100, 0.05, 1);
    state.steerMix = clamp(Number(document.getElementById('driveSteerMix').value || 50) / 100, 0, 1);
    state.steerBias = clamp(Number(document.getElementById('driveSteerBias').value || 0) / 100, -0.5, 0.5);
    await postJson('/api/motor/apply', {
      left_direction: Number(document.getElementById('leftDirection').value || 1),
      right_direction: Number(document.getElementById('rightDirection').value || 1),
      steering_direction: Number(document.getElementById('steeringDirection').value || 1),
      left_max_speed: Number(document.getElementById('leftMaxSpeed').value || 1),
      right_max_speed: Number(document.getElementById('rightMaxSpeed').value || 1),
      left_bias: Number(document.getElementById('leftBias').value || 0),
      right_bias: Number(document.getElementById('rightBias').value || 0),
    });
    await postJson('/api/control', {
      max_throttle: state.maxThrottle,
      steer_mix: state.steerMix,
      steer_bias: state.steerBias,
      steering: state.manualSteering,
      throttle: state.manualThrottle,
    });
    setBanner('driveSettingsMessage', 'Drive settings saved.', 'good');
    await pollStatus();
  } catch (error) {
    setBanner('driveSettingsMessage', error.message || 'Drive settings failed.', 'warn');
  }
}

async function togglePreview() {
  try {
    state.previewEnabled = !state.previewEnabled;
    await postJson('/api/camera/preview_state', { enabled: state.previewEnabled });
    const video = document.getElementById('videoFeed');
    if (!state.previewEnabled) {
      video.classList.add('hidden');
      document.getElementById('viewerFallback').classList.remove('hidden');
      document.getElementById('viewerFallback').textContent = 'Preview paused.';
    } else {
      video.classList.remove('hidden');
      document.getElementById('viewerFallback').classList.add('hidden');
      video.src = `/video_feed?ts=${Date.now()}`;
    }
    await pollStatus();
  } catch (error) {
    setBanner('systemMessage', error.message || 'Preview toggle failed.', 'warn');
  }
}

async function setEstop(enabled) {
  syncEstopToggle(enabled);
  try {
    await postJson('/api/system/estop', { enabled });
    state.estopEnabled = enabled;
    if (enabled) releaseDrivePad();
    await pollStatus();
  } catch (error) {
    syncEstopToggle(state.estopEnabled);
    setBanner('systemMessage', error.message || 'E-stop failed.', 'warn');
  }
}

function bindHoldAction(buttonId, actionStart, actionStop) {
  const button = document.getElementById(buttonId);
  if (!button) return;
  const stop = async () => {
    try {
      if (actionStop) await postJson('/api/arm/action', { action: actionStop });
      await pollStatus();
    } catch (error) {
      setBanner('armMessage', error.message || 'Arm stop failed.', 'warn');
    }
  };
  const start = async () => {
    try {
      await postJson('/api/arm/action', { action: actionStart });
      await pollStatus();
    } catch (error) {
      setBanner('armMessage', error.message || 'Arm action failed.', 'warn');
    }
  };
  button.addEventListener('pointerdown', (event) => { event.preventDefault(); start(); });
  ['pointerup', 'pointerleave', 'pointercancel'].forEach((name) => button.addEventListener(name, stop));
}

function bindClickAction(buttonId, action) {
  const button = document.getElementById(buttonId);
  if (!button) return;
  button.addEventListener('click', async () => {
    try {
      await postJson('/api/arm/action', { action });
      await pollStatus();
    } catch (error) {
      setBanner('armMessage', error.message || 'Arm action failed.', 'warn');
    }
  });
}

function setupStyleSettings() {
  document.getElementById('openStyleSettingsBtn').addEventListener('click', () => {
    syncStyleInputsFromCurrentVars();
    openModal('styleSettingsModal');
  });
  document.getElementById('closeStyleSettingsBtn').addEventListener('click', () => closeModal('styleSettingsModal'));
  document.getElementById('saveStyleSettingsBtn').addEventListener('click', () => {
    styleManager()?.saveCustomOverrides?.(collectStyleOverridesFromInputs());
    setBanner('styleSettingsMessage', 'Style settings saved.', 'good');
    closeModal('styleSettingsModal');
  });
  document.getElementById('resetStyleSettingsBtn').addEventListener('click', () => {
    styleManager()?.resetCustomOverrides?.();
    syncStyleInputsFromCurrentVars();
    setBanner('styleSettingsMessage', 'Style settings reset.', 'good');
  });
  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    el.addEventListener('input', previewStyleOverridesFromInputs);
  });
}

function setupDriveSettings() {
  document.getElementById('openDriveSettingsBtn').addEventListener('click', async () => {
    await pollStatus();
    openModal('driveSettingsModal');
  });
  document.getElementById('closeDriveSettingsBtn').addEventListener('click', () => closeModal('driveSettingsModal'));
  document.getElementById('saveDriveSettingsBtn').addEventListener('click', saveDriveSettings);
  ['driveMaxThrottle', 'driveSteerMix', 'driveSteerBias'].forEach((id) => {
    document.getElementById(id).addEventListener('input', () => {
      if (id === 'driveMaxThrottle') setText('driveMaxThrottleValue', fmt(Number(document.getElementById(id).value) / 100));
      if (id === 'driveSteerMix') setText('driveSteerMixValue', fmt(Number(document.getElementById(id).value) / 100));
      if (id === 'driveSteerBias') setText('driveSteerBiasValue', fmt(Number(document.getElementById(id).value) / 100));
    });
  });
}

async function refreshAiModels(selectedName = null) {
  try {
    const data = await fetchJson('/api/ai/models');
    state.aiModels = data.models || [];
    const targetName = selectedName || data.ai_status?.active_model || 'none';
    renderAiModelOptions(targetName);
    if (!state.aiSettingsLoaded) populateAiSettings({ ai_status: data.ai_status });
    return data;
  } catch (error) {
    setBanner('aiSettingsMessage', error.message || 'Could not refresh AI models.', 'warn');
    throw error;
  }
}

async function uploadAiFiles() {
  const input = document.getElementById('aiUploadFiles');
  const files = Array.from(input.files || []);
  if (!files.length) {
    setBanner('aiSettingsMessage', 'Choose at least one .tflite, .txt, or .json file first.', 'warn');
    return;
  }
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  try {
    const response = await fetch('/api/ai/upload', { method: 'POST', body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || 'Upload failed.');
    setBanner('aiSettingsMessage', data.message || 'Files uploaded.', 'good');
    input.value = '';
    state.aiModels = data.models || [];
    renderAiModelOptions();
  } catch (error) {
    setBanner('aiSettingsMessage', error.message || 'Upload failed.', 'warn');
  }
}

async function deleteAiModel() {
  const model = document.getElementById('aiModelSelect').value;
  if (!model) {
    setBanner('aiSettingsMessage', 'Select a model to delete.', 'warn');
    return;
  }
  try {
    const data = await postJson('/api/ai/delete', { model });
    setBanner('aiSettingsMessage', data.message || 'Model deleted.', 'good');
    state.aiModels = data.models || [];
    renderAiModelOptions();
    await pollStatus();
  } catch (error) {
    setBanner('aiSettingsMessage', error.message || 'Delete failed.', 'warn');
  }
}

async function deployAiModel() {
  const model = document.getElementById('aiModelSelect').value;
  if (!model) {
    setBanner('aiSettingsMessage', 'Select a model to deploy.', 'warn');
    return;
  }
  try {
    const data = await postJson('/api/ai/deploy', {
      model,
      confidence_threshold: Number(document.getElementById('aiConfidenceThreshold').value || 0.25),
      iou_threshold: Number(document.getElementById('aiIouThreshold').value || 0.45),
      overlay_enabled: document.getElementById('aiOverlayEnabled').value === 'true',
      max_overlay_fps: Number(document.getElementById('aiOverlayFps').value || 6.0),
    });
    setBanner('aiSettingsMessage', data.message || 'Model deployed.', 'good');
    state.aiSettingsLoaded = false;
    const video = document.getElementById('videoFeed');
    if (video) video.src = `/video_feed?ts=${Date.now()}`;
    await pollStatus();
    await refreshAiModels(model);
  } catch (error) {
    setBanner('aiSettingsMessage', error.message || 'Deploy failed.', 'warn');
  }
}

async function saveAiConfigOnly() {
  try {
    const currentModel = document.getElementById('aiModelSelect').value || 'none';
    const data = await postJson('/api/ai/config', {
      deployed_model: currentModel,
      confidence_threshold: Number(document.getElementById('aiConfidenceThreshold').value || 0.25),
      iou_threshold: Number(document.getElementById('aiIouThreshold').value || 0.45),
      overlay_enabled: document.getElementById('aiOverlayEnabled').value === 'true',
      max_overlay_fps: Number(document.getElementById('aiOverlayFps').value || 6.0),
    });
    setBanner('aiSettingsMessage', data.message || 'AI settings saved.', 'good');
    await pollStatus();
  } catch (error) {
    setBanner('aiSettingsMessage', error.message || 'AI settings save failed.', 'warn');
  }
}

function setupAiSettings() {
  document.getElementById('openAiSettingsBtn').addEventListener('click', async () => {
    await refreshAiModels(document.getElementById('aiModelSelect').value || null);
    state.aiSettingsLoaded = false;
    await pollStatus();
    openModal('aiSettingsModal');
  });
  document.getElementById('closeAiSettingsBtn').addEventListener('click', () => closeModal('aiSettingsModal'));
  document.getElementById('refreshAiModelsBtn').addEventListener('click', () => refreshAiModels(document.getElementById('aiModelSelect').value || null));
  document.getElementById('uploadAiFilesBtn').addEventListener('click', uploadAiFiles);
  document.getElementById('deleteAiModelBtn').addEventListener('click', deleteAiModel);
  document.getElementById('deployAiModelBtn').addEventListener('click', deployAiModel);
  ['aiConfidenceThreshold', 'aiIouThreshold', 'aiOverlayEnabled', 'aiOverlayFps', 'aiModelSelect'].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', saveAiConfigOnly);
  });
}

function setupDrivePad() {
  const area = document.getElementById('joystickArea');
  area.addEventListener('pointerdown', (event) => {
    area.setPointerCapture(event.pointerId);
    applyDrivePadPosition(event.clientX, event.clientY);
  });
  area.addEventListener('pointermove', (event) => {
    if (event.buttons) applyDrivePadPosition(event.clientX, event.clientY);
  });
  ['pointerup', 'pointerleave', 'pointercancel'].forEach((name) => area.addEventListener(name, releaseDrivePad));
  syncManualReadout();
}

function setupArmControls() {
  bindHoldAction('armUpBtn', 'start_up', 'stop');
  bindHoldAction('armDownBtn', 'start_down', 'stop');
  bindHoldAction('armOpenBtn', 'start_open', 'stop_grip');
  bindHoldAction('armCloseBtn', 'start_close', 'stop_grip');
}

function setupSystemActions() {
  document.getElementById('previewToggleBtn').addEventListener('click', togglePreview);
  document.getElementById('estopToggle').addEventListener('change', (event) => setEstop(event.target.checked));
  const video = document.getElementById('videoFeed');
  video.addEventListener('error', () => {
    document.getElementById('viewerFallback').classList.remove('hidden');
    setBanner('systemMessage', 'Camera preview stream failed to load.', 'warn');
  });
  video.addEventListener('load', () => {
    document.getElementById('viewerFallback').classList.add('hidden');
  });
  video.addEventListener('loadeddata', () => {
    document.getElementById('viewerFallback').classList.add('hidden');
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  setupStyleSettings();
  setupDriveSettings();
  setupAiSettings();
  setupDrivePad();
  setupArmControls();
  setupSystemActions();
  syncStyleInputsFromCurrentVars();
  await pollStatus();
  await refreshAiModels();
  state.statusTimer = window.setInterval(pollStatus, 350);
});
