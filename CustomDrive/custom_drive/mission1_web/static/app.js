const STATUS_REFRESH_MS = 600;
const FRAME_REFRESH_MS = 250;
let refreshInFlight = false;
let refreshTimer = null;
let frameTimer = null;
let frameRequestInFlight = false;
let latestFrameRequestId = 0;
let currentStatus = null;

function shouldShowLiveFrame(status) {
  if (!status) return false;
  const camera = status.camera || {};
  const phase = String(status.phase || '');
  return Boolean(camera.running) && phase.startsWith('ai');
}

function scheduleRefresh(delay = STATUS_REFRESH_MS) {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(refresh, delay);
}

function scheduleFrameRefresh(delay = FRAME_REFRESH_MS) {
  if (frameTimer) clearTimeout(frameTimer);
  frameTimer = setTimeout(refreshFrame, delay);
}

async function fetchJSON(path, options = undefined) {
  const res = await fetch(path, options);
  let data = {};
  try {
    data = await res.json();
  } catch (_err) {
    data = {};
  }
  if (!res.ok) {
    throw new Error(data.message || `Request failed: ${res.status}`);
  }
  return data;
}

async function postJSON(path, body = {}) {
  return fetchJSON(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function fmt(value, digits = 2) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits) : '0.00';
}

function fmtShort(value, digits = 1) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(digits).replace(/\.0+$/, '') : '0';
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function setMessage(id, message, isError = false) {
  const el = document.getElementById(id);
  el.textContent = message || '';
  el.classList.toggle('error', Boolean(isError));
}

function defaultArmPositions() {
  return {
    '1': { servo0: 110, servo1: 110, servo2: 130 },
    '2': { servo0: 92, servo1: 92, servo2: 128 },
    '3': { servo0: 92, servo1: 92, servo2: 72 },
    '4': { servo0: 62, servo1: 62, servo2: 72 },
    '5': { servo0: 110, servo1: 110, servo2: 130 },
    '6': { servo0: 90, servo1: 90, servo2: 90 },
    '7': { servo0: 90, servo1: 90, servo2: 90 },
    '8': { servo0: 90, servo1: 90, servo2: 90 },
  };
}

function normalizeArmPositions(positions) {
  const defaults = defaultArmPositions();
  const merged = { ...defaults, ...(positions || {}) };
  const keys = Object.keys(merged)
    .filter((key) => /^\d+$/.test(String(key)))
    .sort((a, b) => Number(a) - Number(b));
  const out = {};
  for (const key of keys) {
    const source = merged[key] || {};
    const fallback = defaults[key] || { servo0: 90, servo1: 90, servo2: 90 };
    out[key] = {
      servo0: Number(source.servo0 ?? fallback.servo0 ?? 90),
      servo1: Number(source.servo1 ?? fallback.servo1 ?? 90),
      servo2: Number(source.servo2 ?? fallback.servo2 ?? 90),
    };
  }
  return out;
}

function renderArmConfig(armConfig) {
  const positions = normalizeArmPositions(armConfig?.positions || {});
  const roles = armConfig?.roles || {};
  const body = document.getElementById('armPositionsBody');
  body.innerHTML = '';
  for (const key of Object.keys(positions)) {
    const pose = positions[key];
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="arm-pose-id">${escapeHtml(key)}</td>
      <td><input class="arm-angle" data-position="${escapeHtml(key)}" data-servo="servo0" type="number" min="0" max="180" step="1" value="${escapeHtml(pose.servo0)}" /></td>
      <td><input class="arm-angle" data-position="${escapeHtml(key)}" data-servo="servo1" type="number" min="0" max="180" step="1" value="${escapeHtml(pose.servo1)}" /></td>
      <td><input class="arm-angle" data-position="${escapeHtml(key)}" data-servo="servo2" type="number" min="0" max="180" step="1" value="${escapeHtml(pose.servo2)}" /></td>
    `;
    body.appendChild(row);
  }

  const selectMap = {
    armRoleStarting: roles.starting_position ?? 1,
    armRoleGripReady: roles.grip_ready ?? 2,
    armRoleGrip: roles.grip ?? 3,
    armRoleGripAndLift: roles.grip_and_lift ?? 4,
    armRoleRelease: roles.release ?? 5,
  };
  for (const [id, selected] of Object.entries(selectMap)) {
    const select = document.getElementById(id);
    select.innerHTML = '';
    for (const key of Object.keys(positions)) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = `Pose ${key}`;
      option.selected = Number(selected) === Number(key);
      select.appendChild(option);
    }
  }

  document.getElementById('armPoseSettle').value = armConfig?.pose_settle_s ?? 0.45;
  document.getElementById('armGripYRatio').value = armConfig?.grip_trigger_y_ratio ?? 0.30;
}

function collectArmConfig() {
  const positions = {};
  document.querySelectorAll('#armPositionsBody input.arm-angle').forEach((input) => {
    const position = String(input.dataset.position || '').trim();
    const servo = String(input.dataset.servo || '').trim();
    if (!position || !servo) return;
    if (!positions[position]) {
      positions[position] = {};
    }
    positions[position][servo] = Number(input.value || 0);
  });
  return {
    enabled: true,
    pose_settle_s: Number(document.getElementById('armPoseSettle').value || 0.45),
    grip_trigger_y_ratio: Number(document.getElementById('armGripYRatio').value || 0.30),
    positions,
    roles: {
      starting_position: Number(document.getElementById('armRoleStarting').value || 1),
      grip_ready: Number(document.getElementById('armRoleGripReady').value || 2),
      grip: Number(document.getElementById('armRoleGrip').value || 3),
      grip_and_lift: Number(document.getElementById('armRoleGripAndLift').value || 4),
      release: Number(document.getElementById('armRoleRelease').value || 5),
    },
  };
}

function populateConfig(config) {
  const session = config.session || {};
  const drive = config.drive || {};
  const arm = config.arm || {};
  document.getElementById('routeText').value = session.route_text || '';
  document.getElementById('targetClassId').value = session.target_class_id ?? 1;
  document.getElementById('confidenceThreshold').value = session.confidence_threshold ?? 0.25;
  document.getElementById('iouThreshold').value = session.iou_threshold ?? 0.45;
  document.getElementById('loopTick').value = session.loop_tick_s ?? 0.08;
  document.getElementById('forwardSpeed').value = drive.forward_speed ?? drive.approach_speed ?? 0.22;
  document.getElementById('turnK').value = drive.turn_k ?? 0.005;
  document.getElementById('turnSpeedMax').value = drive.turn_speed_max ?? drive.max_steering ?? 0.75;
  document.getElementById('deadbandRatio').value = drive.target_x_deadband_ratio ?? 0.05;
  renderArmConfig(arm);
}

function collectConfig() {
  return {
    session: {
      route_text: document.getElementById('routeText').value || '',
      target_class_id: Number(document.getElementById('targetClassId').value || 1),
      confidence_threshold: Number(document.getElementById('confidenceThreshold').value || 0.25),
      iou_threshold: Number(document.getElementById('iouThreshold').value || 0.45),
      loop_tick_s: Number(document.getElementById('loopTick').value || 0.08),
    },
    drive: {
      forward_speed: Number(document.getElementById('forwardSpeed').value || 0.22),
      turn_k: Number(document.getElementById('turnK').value || 0.005),
      turn_speed_max: Number(document.getElementById('turnSpeedMax').value || 0.75),
      target_x_deadband_ratio: Number(document.getElementById('deadbandRatio').value || 0.05),
    },
    arm: collectArmConfig(),
  };
}


function renderModelList(status) {
  const select = document.getElementById('modelSelect');
  const models = status.models || [];
  const selected = status.selected_model || status.active_model || '';
  select.innerHTML = '';
  if (!models.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No uploaded models';
    select.appendChild(option);
    return;
  }
  for (const model of models) {
    const option = document.createElement('option');
    option.value = model;
    option.textContent = model;
    option.selected = model === selected;
    select.appendChild(option);
  }
}

function renderDetections(status) {
  const body = document.getElementById('detectionsBody');
  const detections = status.detections || [];
  body.innerHTML = '';
  if (!detections.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty-cell">No detections in the latest AI output.</td></tr>';
    return;
  }
  for (const det of detections) {
    const row = document.createElement('tr');
    if (det.is_target_class) {
      row.classList.add('target-row');
    }
    row.innerHTML = `
      <td>${escapeHtml(det.class_id)}</td>
      <td>${fmt(det.confidence, 3)}</td>
      <td>${fmt(det.center?.x, 1)}</td>
      <td>${fmt(det.center?.y, 1)}</td>
      <td>${fmt(det.box?.width, 1)}</td>
      <td>${fmt(det.box?.height, 1)}</td>
      <td>${det.is_target_class ? 'yes' : ''}</td>
    `;
    body.appendChild(row);
  }
}

function renderSummaryCards(status) {
  const cards = document.getElementById('summaryCards');
  const detections = status.detections || [];
  const pipeline = status.pipeline || {};
  const camera = status.camera || {};
  const target = status.target_detection || {};
  const targetCenter = target.center || {};
  const armSequence = status.arm_sequence || {};
  const items = [
    { label: 'Phase', value: status.phase || 'idle' },
    { label: 'Mission state', value: status.mission_state || '-' },
    { label: 'Objects', value: String(detections.length) },
    { label: 'Target side', value: status.target_side || '-' },
    { label: 'Holding', value: status.held_class_id ?? '-' },
    { label: 'Car turn', value: status.car_turn_direction || '-' },
    { label: 'Target X', value: fmtShort(targetCenter.x, 1) },
    { label: 'Pipeline FPS', value: `${fmtShort(pipeline.fps || 0, 2)} fps` },
    { label: 'Arm stage', value: armSequence.state || 'idle' },
    { label: 'Arm pose', value: armSequence.last_pose_number ? `#${armSequence.last_pose_number}` : '-' },
    { label: 'Camera FPS', value: `${fmtShort(camera.fps || 0, 1)} fps` },
    { label: 'Loaded model', value: status.loaded_model || 'none' },
  ];
  cards.innerHTML = items.map((item) => `
    <div class="summary-card">
      <div class="summary-label">${escapeHtml(item.label)}</div>
      <div class="summary-value">${escapeHtml(item.value)}</div>
    </div>
  `).join('');
}

function renderStatus(status) {
  const statusEl = document.getElementById('status');
  const camera = status.camera || {};
  const motor = status.motor_config || {};
  const pipeline = status.pipeline || {};
  const target = status.target_detection || {};
  const targetCenter = target.center || {};
  const targetBox = target.box || {};
  const deadbandRatio = Number(status.config?.drive?.target_x_deadband_ratio || 0.05);
  const armSequence = status.arm_sequence || {};
  const armStatus = status.arm_status || {};
  const armConfig = status.config?.arm || {};
  statusEl.innerHTML = `
    <div class="status-grid">
      <div class="status-label">Running</div><div>${escapeHtml(status.running)}</div>
      <div class="status-label">Phase</div><div>${escapeHtml(status.phase)}</div>
      <div class="status-label">Detail</div><div>${escapeHtml(status.detail)}</div>
      <div class="status-label">Selected model</div><div>${escapeHtml(status.selected_model || 'none')}</div>
      <div class="status-label">Loaded model</div><div>${escapeHtml(status.loaded_model || 'none')}</div>
      <div class="status-label">AI backend</div><div>${escapeHtml(status.ai_ready)} | ${escapeHtml(status.ai_message || '')}</div>
      <div class="status-label">Pi pipeline FPS</div><div>${fmt(pipeline.fps || 0, 2)} fps | ${fmt(pipeline.cycle_time_ms || 0, 1)} ms/cycle</div>
      <div class="status-label">Camera</div><div>${escapeHtml(camera.backend || 'offline')} | live=${escapeHtml(camera.preview_live ?? false)} | camera_fps=${fmt(camera.fps || 0, 1)}</div>
      <div class="status-label">Mission state</div><div>${escapeHtml(status.mission_state || '-')}</div>
      <div class="status-label">Pickup classes</div><div>${escapeHtml((status.pickup_classes || []).join('/'))}</div>
      <div class="status-label">Holding class</div><div>${escapeHtml(status.held_class_id ?? '-')}</div>
      <div class="status-label">Drop-off class</div><div>${escapeHtml(status.dropoff_target_class_id ?? '-')}</div>
      <div class="status-label">Pickup lock</div><div>${escapeHtml(status.pickup_target_class_id ?? '-')}</div>
      <div class="status-label">Target found</div><div>${escapeHtml(status.target_found)}</div>
      <div class="status-label">Target side</div><div>${escapeHtml(status.target_side || '-')}</div>
      <div class="status-label">Car turn</div><div>${escapeHtml(status.car_turn_direction || '-')}</div>
      <div class="status-label">Target center</div><div>x=${fmt(targetCenter.x, 1)} y=${fmt(targetCenter.y, 1)}</div>
      <div class="status-label">Target box</div><div>w=${fmt(targetBox.width, 1)} h=${fmt(targetBox.height, 1)}</div>
      <div class="status-label">Forward deadband</div><div>${fmt(deadbandRatio * 100, 1)}% of frame width</div>
      <div class="status-label">Arm backend</div><div>enabled=${escapeHtml(armStatus.enabled ?? false)} | available=${escapeHtml(armStatus.available ?? false)} | ${escapeHtml(armStatus.backend || 'disabled')}</div>
      <div class="status-label">Arm sequence</div><div>${escapeHtml(armSequence.state || 'idle')} | ${escapeHtml(armSequence.note || '-')}</div>
      <div class="status-label">Arm pose map</div><div>start=#${escapeHtml(armConfig.roles?.starting_position ?? '-')} ready=#${escapeHtml(armConfig.roles?.grip_ready ?? '-')} grip=#${escapeHtml(armConfig.roles?.grip ?? '-')} lift=#${escapeHtml(armConfig.roles?.grip_and_lift ?? '-')} release=#${escapeHtml(armConfig.roles?.release ?? '-')}</div>
      <div class="status-label">Arm angles</div><div>servo0=${fmt(armStatus.servo0_angle, 0)} servo1=${fmt(armStatus.servo1_angle, 0)} servo2=${fmt(armStatus.grip_angle, 0)}</div>
      <div class="status-label">Command</div><div>left=${fmt(status.last_command?.left, 2)} right=${fmt(status.last_command?.right, 2)} note=${escapeHtml(status.last_command?.note || '')}</div>
      <div class="status-label">Motor GPIO</div><div>${escapeHtml(motor.gpio_available ?? false)}</div>
      <div class="status-label">Output summary</div><div>${escapeHtml(status.last_output_summary || '-')}</div>
      <div class="status-label">Arm status</div><div>${escapeHtml(armStatus.last_message || '-')}</div>
      <div class="status-label">Last error</div><div>${escapeHtml(status.last_error || camera.error || armStatus.last_error || '-')}</div>
    </div>
  `;

  const events = document.getElementById('events');
  events.textContent = (status.events || []).map((entry) => {
    const extra = Object.entries(entry)
      .filter(([key]) => !['timestamp', 'level', 'type', 'message'].includes(key))
      .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
      .join(' ');
    return `[${fmt(entry.timestamp, 2)}] ${String(entry.level || 'info').toUpperCase()} ${entry.type || 'runtime'}: ${entry.message}${extra ? ` | ${extra}` : ''}`;
  }).join('\n');

  renderModelList(status);
  renderDetections(status);
  renderSummaryCards(status);
  renderViewer(status);
}

function renderOverlay(status) {
  const svg = document.getElementById('viewerOverlay');
  const frame = status.frame || {};
  const width = Math.max(1, Number(frame.width || 640));
  const height = Math.max(1, Number(frame.height || 360));
  const detections = status.detections || [];
  const deadbandRatio = Number(status.config?.drive?.target_x_deadband_ratio || 0.05);
  const deadbandWidth = width * deadbandRatio;
  const leftBand = width / 2 - deadbandWidth;
  const rightBand = width / 2 + deadbandWidth;

  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';

  const guideGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  guideGroup.setAttribute('class', 'overlay-guides');
  guideGroup.innerHTML = `
    <rect x="${leftBand}" y="0" width="${rightBand - leftBand}" height="${height}" class="overlay-deadband" />
    <line x1="${width / 2}" y1="0" x2="${width / 2}" y2="${height}" class="overlay-axis" />
    <line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" class="overlay-axis" />
  `;
  svg.appendChild(guideGroup);

  const target = detections.find((det) => det && det.is_target_class) || null;
  if (target) {
    const targetGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    targetGroup.setAttribute('class', 'overlay-guides');
    const cx = Number(target.center?.x_raw || ((target.box?.x1 || 0) + (target.box?.x2 || 0)) / 2);
    const cy = Number(target.center?.y_raw || ((target.box?.y1 || 0) + (target.box?.y2 || 0)) / 2);
    targetGroup.innerHTML = `
      <circle cx="${cx}" cy="${cy}" r="6" class="box-center-dot" />
    `;
    svg.appendChild(targetGroup);
  }
}

function renderViewer(status) {
  const video = document.getElementById('videoFeed');
  const svg = document.getElementById('viewerOverlay');
  const note = document.getElementById('viewerNote');
  const stats = document.getElementById('viewerStats');
  const phase = status.phase || '';
  const liveFrameVisible = shouldShowLiveFrame(status);
  const pipelineFps = fmt(status.pipeline?.fps || 0, 2);
  const detectionCount = String((status.detections || []).length);
  stats.innerHTML = `
    <span class="stat-pill">Objects ${escapeHtml(detectionCount)}</span>
    <span class="stat-pill">FPS ${escapeHtml(pipelineFps)}</span>
    <span class="stat-pill">State ${escapeHtml(status.mission_state || 'idle')}</span>
    <span class="stat-pill">Holding ${escapeHtml(status.held_class_id ?? '-')}</span>
    <span class="stat-pill">Target ${escapeHtml(status.target_side || 'none')}</span>
    <span class="stat-pill">Turn ${escapeHtml(status.car_turn_direction || 'stopped')}</span>
  `;

  if (liveFrameVisible) {
    video.style.display = 'block';
    svg.style.display = 'block';
    renderOverlay(status);
    note.textContent = `Showing the Pi-generated annotated frame with a light guide overlay only. Mission state: ${status.mission_state || 'idle'}. Holding class: ${status.held_class_id ?? '-'}. Drop-off class: ${status.dropoff_target_class_id ?? '-'}. Target side: ${status.target_side || 'none'}. Car turn: ${status.car_turn_direction || 'stopped'}. Arm stage: ${status.arm_sequence?.state || 'idle'}.`;
  } else if (phase === 'start_route' || phase === 'route_pending') {
    video.style.display = 'none';
    svg.style.display = 'none';
    svg.innerHTML = '';
    note.textContent = 'Camera is still off while the start route is running.';
  } else {
    video.style.display = 'none';
    svg.style.display = 'none';
    svg.innerHTML = '';
    note.textContent = 'Annotated frame and object boxes will appear here after the route, camera start, and model load steps complete.';
  }
}

async function saveConfig() {
  try {
    const data = await postJSON('/api/config', collectConfig());
    populateConfig(data.config || {});
    setMessage('configMessage', data.message || 'Mission 1 config saved.');
    setMessage('armMessage', 'Mission 1 arm pose config saved.');
    await refresh();
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to save config.', true);
    setMessage('armMessage', err.message || 'Failed to save Mission 1 arm pose config.', true);
  }
}

async function startMission() {
  try {
    await saveConfig();
    const route_text = document.getElementById('routeText').value || '';
    const data = await postJSON('/api/session/start', { route_text });
    setMessage('configMessage', data.message || 'Mission 1 session started.');
    await refresh();
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to start Mission 1 session.', true);
  }
}

async function stopMission() {
  try {
    const data = await postJSON('/api/session/stop');
    setMessage('configMessage', data.message || 'Mission 1 session stopped.');
    await refresh();
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to stop Mission 1 session.', true);
  }
}

async function uploadModel() {
  const input = document.getElementById('modelUpload');
  const file = input.files && input.files[0];
  if (!file) {
    setMessage('modelMessage', 'Choose a .tflite model first.', true);
    return;
  }
  const formData = new FormData();
  formData.append('model', file);
  try {
    const res = await fetch('/api/models/upload', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.message || `Request failed: ${res.status}`);
    }
    input.value = '';
    setMessage('modelMessage', data.message || 'Model uploaded and selected.');
    await refresh();
  } catch (err) {
    setMessage('modelMessage', err.message || 'Failed to upload model.', true);
  }
}

async function loadSelectedModel() {
  const select = document.getElementById('modelSelect');
  if (!select.value) {
    setMessage('modelMessage', 'No uploaded model selected.', true);
    return;
  }
  try {
    const data = await postJSON('/api/model/select', { name: select.value });
    setMessage('modelMessage', data.message || 'Model selected.');
    await refresh();
  } catch (err) {
    setMessage('modelMessage', err.message || 'Failed to set model.', true);
  }
}

async function loadArmRole(role) {
  try {
    await saveConfig();
    const data = await postJSON('/api/arm/load_role', { role });
    setMessage('armMessage', data.message || `Loaded ${role} pose.`);
    await refresh();
  } catch (err) {
    setMessage('armMessage', err.message || `Failed to load ${role} pose.`, true);
  }
}

async function refresh() {
  if (refreshInFlight) {
    return;
  }
  refreshInFlight = true;
  try {
    const status = await fetchJSON('/api/status');
    currentStatus = status;
    renderStatus(status);
  } catch (err) {
    setMessage('configMessage', err.message || 'Refresh failed.', true);
  } finally {
    refreshInFlight = false;
    scheduleRefresh();
  }
}

function refreshFrame() {
  const video = document.getElementById('videoFeed');
  const svg = document.getElementById('viewerOverlay');
  if (!shouldShowLiveFrame(currentStatus)) {
    frameRequestInFlight = false;
    if (video) {
      video.removeAttribute('src');
      video.style.display = 'none';
    }
    if (svg) {
      svg.style.display = 'none';
    }
    scheduleFrameRefresh();
    return;
  }
  if (!video) {
    scheduleFrameRefresh();
    return;
  }
  if (frameRequestInFlight) {
    scheduleFrameRefresh();
    return;
  }

  frameRequestInFlight = true;
  const requestId = ++latestFrameRequestId;
  const finish = () => {
    if (requestId === latestFrameRequestId) {
      frameRequestInFlight = false;
    }
  };

  video.onload = finish;
  video.onerror = finish;
  video.src = `/api/frame.jpg?t=${Date.now()}`;
  window.setTimeout(finish, Math.max(800, FRAME_REFRESH_MS * 3));
  scheduleFrameRefresh();
}

async function init() {
  try {
    const configData = await fetchJSON('/api/config');
    if (configData.ok && configData.config) {
      populateConfig(configData.config);
    }
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to load config.', true);
  }
  await refresh();
  scheduleFrameRefresh();
}

document.getElementById('saveConfigBtn').onclick = saveConfig;
document.getElementById('startBtn').onclick = startMission;
document.getElementById('stopBtn').onclick = stopMission;
document.getElementById('uploadModelBtn').onclick = uploadModel;
document.getElementById('loadModelBtn').onclick = loadSelectedModel;
document.querySelectorAll('.arm-load-role').forEach((button) => {
  button.onclick = () => loadArmRole(String(button.dataset.role || ''));
});

init();
