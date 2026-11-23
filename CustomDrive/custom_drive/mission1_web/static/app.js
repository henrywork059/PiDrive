const STATUS_REFRESH_MS = 600;
const FRAME_REFRESH_MS = 250;
let refreshInFlight = false;
let refreshTimer = null;
let frameTimer = null;
let frameRequestInFlight = false;
let latestFrameRequestId = 0;
let currentStatus = null;
let triggerPreviewEdited = false; // draft frame guide only; never writes server config
let statusFailures = 0;
let frameFailures = 0;

function shouldShowLiveFrame(status) {
  if (!status) return false;
  const camera = status.camera || {};
  const phase = String(status.phase || '');
  return Boolean(camera.running) && phase.startsWith('ai');
}

// R43: only browser observation intervals change; motor/arm/mission timing is untouched.
function statusRefreshDelay() {
  if (document.hidden) return 5000;
  const active = Boolean(currentStatus?.running) ||
    String(currentStatus?.phase || '').startsWith('ai');
  const base = active ? STATUS_REFRESH_MS : 2500;
  return Math.min(8000, base * Math.pow(2, Math.min(4, statusFailures)));
}
function frameRefreshDelay() {
  if (document.hidden) return 5000;
  if (!shouldShowLiveFrame(currentStatus)) return 2000;
  return Math.min(4000, FRAME_REFRESH_MS * Math.pow(2, Math.min(4, frameFailures)));
}
function scheduleRefresh(delay = statusRefreshDelay()) {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => {
    refreshTimer = null;
    void refresh();
  }, delay);
}
function scheduleFrameRefresh(delay = frameRefreshDelay()) {
  if (frameTimer) clearTimeout(frameTimer);
  frameTimer = setTimeout(() => {
    frameTimer = null;
    refreshFrame();
  }, delay);
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
    const fallback = res.status === 403 ? 'Permission denied. Open Mission 1 using an authorized Pi connection.'
      : res.status === 401 ? 'Session expired. Reconnect to the Pi, then retry.'
      : res.status >= 500 ? 'Mission 1 service unavailable. Check the Pi, then Refresh.'
      : `Request failed (${res.status}). Check inputs, then retry.`;
    throw new Error(data.message || fallback);
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

function themeToCssVars(theme) {
  const rgb = Array.isArray(theme?.rgb) ? theme.rgb.join(', ') : '148, 163, 184';
  const hex = theme?.hex || '#94a3b8';
  const panelHex = theme?.panel_hex || '#1f2937';
  return `--theme-rgb:${rgb}; --theme-hex:${hex}; --theme-panel:${panelHex};`;
}

function themeBadge(label, theme, extraClass = '') {
  return `<span class="theme-badge ${escapeHtml(extraClass)}" style="${escapeHtml(themeToCssVars(theme))}">${escapeHtml(label)}</span>`;
}

function directionLabel(value, deadband = 0.03) {
  const num = Number(value || 0);
  if (!Number.isFinite(num) || Math.abs(num) <= deadband) return 'stopped';
  return num > 0 ? 'forward' : 'reverse';
}

function directionClass(direction) {
  switch (String(direction || '').toLowerCase()) {
    case 'forward':
      return 'dir-forward';
    case 'reverse':
      return 'dir-reverse';
    case 'clockwise':
      return 'dir-clockwise';
    case 'counterclockwise':
      return 'dir-counterclockwise';
    case 'pivot_left':
    case 'pivot_right':
      return 'dir-pivot';
    default:
      return 'dir-stopped';
  }
}

function formatDirectionLabel(direction) {
  return String(direction || 'stopped').replaceAll('_', ' ');
}

function motorRotationLabel(motorStatus) {
  return formatDirectionLabel(String(motorStatus?.vehicle_rotation || 'stopped'));
}

function directionSettingLabel(value) {
  return Number(value || 1) < 0 ? 'Inverted (-1)' : 'Normal (+1)';
}

function invertDirectionValue(value) {
  return Number(value || 1) < 0 ? 1 : -1;
}

function themePanelCard(content, theme, extraClass = '') {
  return `<div class="themed-block ${escapeHtml(extraClass)}" style="${escapeHtml(themeToCssVars(theme))}">${content}</div>`;
}

function servoBarPercent(angle) {
  const num = Number(angle || 0);
  if (!Number.isFinite(num)) return 0;
  return Math.max(0, Math.min(100, (num / 180) * 100));
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
  document.getElementById('armGripYRatio').value = triggerGuidePercent(armConfig?.grip_trigger_y_ratio ?? 0.30);
  document.getElementById('armDropoffYRatio').value = triggerGuidePercent(armConfig?.dropoff_trigger_y_ratio ?? 0.30);
}

function clampTriggerPercent(raw, fallback = 30) {
  // Preserve valid zero; blank and invalid inputs use the previous safe default.
  if (raw == null || String(raw).trim() === '') return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : fallback;
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
    grip_trigger_y_ratio: clampTriggerPercent(document.getElementById('armGripYRatio').value) / 100,
    dropoff_trigger_y_ratio: clampTriggerPercent(document.getElementById('armDropoffYRatio').value) / 100,
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
  const mission = config.mission || {};
  document.getElementById('routeText').value = session.route_text || '';
  document.getElementById('confidenceThreshold').value = session.confidence_threshold ?? 0.25;
  document.getElementById('iouThreshold').value = session.iou_threshold ?? 0.45;
  document.getElementById('loopTick').value = session.loop_tick_s ?? 0.08;
  document.getElementById('forwardSpeed').value = drive.forward_speed ?? drive.approach_speed ?? 0.22;
  document.getElementById('turnK').value = drive.turn_k ?? 0.005;
  document.getElementById('turnSpeedMax').value = drive.turn_speed_max ?? drive.max_steering ?? 0.75;
  document.getElementById('deadbandRatio').value = drive.target_x_deadband_ratio ?? 0.05;
  document.getElementById('reverseAfterRelease').value = mission.reverse_after_release_s ?? 0.9;
  renderArmConfig(arm);
}

function collectConfig() {
  return {
    session: {
      route_text: document.getElementById('routeText').value || '',
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
    mission: {
      reverse_after_release_s: Number(document.getElementById('reverseAfterRelease').value || 0.9),
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
    option.textContent = 'No models on Pi — upload a .tflite model';
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
  const stageTheme = status.stage_theme || {};
  const motionTheme = status.motion_theme || {};
  const armTheme = status.arm_theme || {};
  const items = [
    { label: 'Phase', value: status.phase || 'idle', theme: stageTheme },
    { label: 'Mission state', value: status.mission_state || '-', theme: stageTheme },
    { label: 'Objects', value: String(detections.length), theme: stageTheme },
    { label: 'Target side', value: status.target_side || '-', theme: motionTheme },
    { label: 'Assumed held', value: status.held_class_id ?? '-', theme: armTheme },
    { label: 'Car turn', value: status.car_turn_direction || '-', theme: motionTheme },
    { label: 'Intended motion', value: status.intended_motion || '-', theme: motionTheme },
    { label: 'Target X', value: fmtShort(targetCenter.x, 1), theme: motionTheme },
    { label: 'Pipeline FPS', value: `${fmtShort(pipeline.fps || 0, 2)} fps`, theme: stageTheme },
    { label: 'Arm stage', value: armSequence.state || 'idle', theme: armTheme },
    { label: 'Arm pose', value: armSequence.last_pose_number ? `#${armSequence.last_pose_number}` : '-', theme: armTheme },
    { label: 'Camera FPS', value: `${fmtShort(camera.fps || 0, 1)} fps`, theme: stageTheme },
    { label: 'Loaded model', value: status.loaded_model || 'none', theme: stageTheme },
  ];
  cards.innerHTML = items.map((item) => `
    <div class="summary-card themed" style="${escapeHtml(themeToCssVars(item.theme || {}))}">
      <div class="summary-label">${escapeHtml(item.label)}</div>
      <div class="summary-value">${escapeHtml(item.value)}</div>
    </div>
  `).join('');
}


function armModeLabel(armStatus) {
  if (armStatus.simulated) return 'simulated';
  if (armStatus.available) return 'hardware';
  return 'unavailable';
}

function motorLogicLabel(steeringDirection) {
  return Number(steeringDirection || 1) < 0 ? 'inverted' : 'normal';
}

function hardwareDirectionButtonHtml(id, title, currentDirection, subtitle) {
  const inverted = Number(currentDirection || 1) < 0;
  const stateLabel = inverted ? 'Inverted' : 'Normal';
  return `
    <button type="button" class="toggle-box-button ${inverted ? 'is-active' : ''}" id="${id}">
      <span class="toggle-box-eyebrow">${escapeHtml(title)}</span>
      <span class="toggle-box-value">${escapeHtml(stateLabel)}</span>
      <span class="toggle-box-sub">${escapeHtml(subtitle)}</span>
    </button>
  `;
}

function turnLogicButtonHtml(id, steeringDirection) {
  const inverted = Number(steeringDirection || 1) < 0;
  return `
    <button type="button" class="toggle-box-button toggle-box-turn ${inverted ? 'is-active' : ''}" id="${id}">
      <span class="toggle-box-eyebrow">Turn logic</span>
      <span class="toggle-box-value">${inverted ? 'Inverted' : 'Normal'}</span>
      <span class="toggle-box-sub">Normal: turn left = left motor back, right motor forward. Inverted flips that software turn mapping.</span>
    </button>
  `;
}

function renderArmPositionPanel(status) {
  const panel = document.getElementById('armPositionPanel');
  const armStatus = status.arm_status || {};
  const armSequence = status.arm_sequence || {};
  const armTheme = status.arm_theme || {};
  const armMode = armModeLabel(armStatus);
  const servoItems = [
    { label: 'Servo 0', angle: armStatus.servo0_angle, channel: armStatus.servo0_channel, moving: armStatus.servo0_moving },
    { label: 'Servo 1', angle: armStatus.servo1_angle, channel: armStatus.servo1_channel, moving: armStatus.servo1_moving, disabled: armStatus.servo1_enabled === false },
    { label: 'Servo 2', angle: armStatus.servo2_angle ?? armStatus.grip_angle, channel: armStatus.servo2_channel ?? armStatus.grip_channel, moving: armStatus.grip_moving },
  ];
  const servoCards = servoItems.map((servo) => {
    const angle = Number(servo.angle ?? 0);
    const moving = Boolean(servo.moving);
    return `
      <div class="arm-servo-card ${servo.disabled ? 'is-disabled' : ''}" style="${escapeHtml(themeToCssVars(armTheme))}">
        <div class="servo-card-head">
          <div>
            <div class="servo-label">${escapeHtml(servo.label)}</div>
            <div class="servo-meta">channel ${escapeHtml(servo.channel ?? '-')}</div>
          </div>
          <span class="mini-badge ${moving ? 'mini-badge-live' : (armStatus.simulated ? 'mini-badge-sim' : 'mini-badge-muted')}">${moving ? 'moving' : (servo.disabled ? 'disabled' : (armStatus.simulated ? 'simulated' : 'held'))}</span>
        </div>
        <div class="servo-angle">${fmtShort(angle, 0)}°</div>
        <div class="servo-bar"><span style="width:${servoBarPercent(angle)}%"></span></div>
      </div>
    `;
  }).join('');

  panel.innerHTML = themePanelCard(`
    <div class="panel-chip-row">
      ${themeBadge(`Arm stage: ${armSequence.state || 'idle'}`, armTheme)}
      ${themeBadge(`Pose: ${armSequence.last_pose_number ? `#${armSequence.last_pose_number}` : '-'}`, armTheme, 'arm-badge')}
      <span class="theme-badge ${armStatus.simulated ? 'sim-badge' : 'neutral-badge'}">Backend ${escapeHtml(armStatus.backend || 'disabled')}</span>
      <span class="theme-badge ${armStatus.simulated ? 'sim-badge' : 'neutral-badge'}">Mode ${escapeHtml(armMode)}</span>
    </div>
    <div class="arm-overview-grid">
      <div class="arm-info-card">
        <div class="info-title">Sequence</div>
        <div class="info-main">${escapeHtml(armSequence.note || '-')}</div>
        <div class="info-sub">last role=${escapeHtml(armSequence.last_pose_role || '-')} · target lock=${escapeHtml(armSequence.target_lock_engaged ?? false)}</div>
      </div>
      <div class="arm-info-card">
        <div class="info-title">Backend status</div>
        <div class="info-main">enabled=${escapeHtml(armStatus.enabled ?? false)} · available=${escapeHtml(armStatus.available ?? false)} · hardware=${escapeHtml(armStatus.hardware_available ?? false)}</div>
        <div class="info-sub">hold refresh=${escapeHtml(armStatus.hold_refresh_running ?? false)} · speed x${fmtShort(armStatus.speed_multiplier ?? 1, 2)}</div>
      </div>
    </div>
    <div class="arm-servo-grid">${servoCards}</div>
    <div class="arm-footer-note ${armStatus.simulated ? 'sim-note' : ''}">${escapeHtml(armStatus.last_message || '-')}</div>
  `, armTheme, 'arm-live-block');
}

function renderMotorPositionPanel(status) {
  const panel = document.getElementById('motorPositionPanel');
  const motorStatus = status.motor_status || {};
  const motorConfig = motorStatus.config || status.motor_config || {};
  const motionTheme = status.motion_theme || {};
  const left = motorStatus.left || {};
  const right = motorStatus.right || {};
  const rotation = motorRotationLabel(motorStatus);
  const leftDirection = String(left.direction || directionLabel(left.value));
  const rightDirection = String(right.direction || directionLabel(right.value));
  const leftPower = Math.max(0, Math.min(100, Number(left.power_ratio || Math.abs(Number(left.value || 0))) * 100));
  const rightPower = Math.max(0, Math.min(100, Number(right.power_ratio || Math.abs(Number(right.value || 0))) * 100));
  const leftDirSetting = Number(motorConfig.left_direction || 1) < 0 ? -1 : 1;
  const rightDirSetting = Number(motorConfig.right_direction || 1) < 0 ? -1 : 1;
  const steeringDirection = Number(motorConfig.steering_direction || 1) < 0 ? -1 : 1;
  const turnLogic = motorLogicLabel(steeringDirection);
  panel.innerHTML = themePanelCard(`
    <div class="panel-chip-row">
      ${themeBadge(`Motion: ${status.intended_motion || 'idle'}`, motionTheme)}
      <span class="theme-badge ${directionClass(motorStatus.vehicle_rotation)}">Rotation ${escapeHtml(rotation)}</span>
      <span class="theme-badge neutral-badge">GPIO ${escapeHtml(motorConfig.gpio_available ?? false)}</span>
      <span class="theme-badge ${turnLogic === 'inverted' ? 'turn-badge-inverted' : 'turn-badge-normal'}">Turn logic ${escapeHtml(turnLogic)}</span>
    </div>
    <div class="motor-grid">
      <div class="motor-card ${directionClass(leftDirection)}">
        <div class="motor-head">
          <div>
            <div class="motor-label">Left motor</div>
            <div class="motor-direction">${escapeHtml(formatDirectionLabel(leftDirection))}</div>
          </div>
          <div class="motor-value">${fmt(Number(left.value || 0), 2)}</div>
        </div>
        <div class="motor-bar"><span style="width:${leftPower}%"></span></div>
        <div class="motor-setting-row">
          ${hardwareDirectionButtonHtml('motorLeftDirectionToggleBtn', 'Left hardware output', leftDirSetting, 'Affects hardware motor output polarity only.')}
        </div>
      </div>
      <div class="motor-card ${directionClass(rightDirection)}">
        <div class="motor-head">
          <div>
            <div class="motor-label">Right motor</div>
            <div class="motor-direction">${escapeHtml(formatDirectionLabel(rightDirection))}</div>
          </div>
          <div class="motor-value">${fmt(Number(right.value || 0), 2)}</div>
        </div>
        <div class="motor-bar"><span style="width:${rightPower}%"></span></div>
        <div class="motor-setting-row">
          ${hardwareDirectionButtonHtml('motorRightDirectionToggleBtn', 'Right hardware output', rightDirSetting, 'Affects hardware motor output polarity only.')}
        </div>
      </div>
    </div>
    <div class="motor-control-grid single-column">
      <div class="motor-hint-card">
        <div class="status-label-inline">Calibration rule</div>
        <div>Hardware output toggles change only the remembered left/right motor polarity. The turn logic control changes the software turn mapping used by both live Mission 1 turning and the start route.</div>
      </div>
      <div class="toggle-box-stack">
        ${turnLogicButtonHtml('turnLogicToggleBtn', steeringDirection)}
      </div>
    </div>
    <div class="motor-footer-grid">
      <div><span class="status-label-inline">Command mode</span> ${escapeHtml(motorStatus.mode || status.last_command?.mode || '-')}</div>
      <div><span class="status-label-inline">Command note</span> ${escapeHtml(motorStatus.note || status.last_command?.note || '-')}</div>
      <div><span class="status-label-inline">Route link</span> Start-route and live Mission 1 outputs both use this same remembered motor calibration and turn logic.</div>
      <div><span class="status-label-inline">Use case</span> Toggle hardware output if a wheel spins opposite to the intended direction. Toggle turn logic if “turn left/right” is swapped.</div>
    </div>
    <div id="motorMessage" class="message"></div>
  `, motionTheme, 'motor-live-block');

  const leftBtn = document.getElementById('motorLeftDirectionToggleBtn');
  if (leftBtn) leftBtn.onclick = () => saveMotorConfig({ left_direction: leftDirSetting < 0 ? 1 : -1 });
  const rightBtn = document.getElementById('motorRightDirectionToggleBtn');
  if (rightBtn) rightBtn.onclick = () => saveMotorConfig({ right_direction: rightDirSetting < 0 ? 1 : -1 });
  const turnBtn = document.getElementById('turnLogicToggleBtn');
  if (turnBtn) turnBtn.onclick = () => saveMotorConfig({ steering_direction: steeringDirection < 0 ? 1 : -1 });
}


function renderMissionTimeline(status) {
  const root = document.getElementById('missionTimeline');
  if (!root) return;
  root.dataset.connection = 'live';
  const disconnection = root.querySelector('.mission-progress-disconnected');
  if (disconnection) disconnection.hidden = true;
  const progress = window.CustomDriveMissionTimeline.project(status);
  // R35: announce stage transitions only; the detailed telemetry can update
  // many times per second without re-announcing the same motor/arm status.
  const announcer = document.getElementById('missionTimelineAnnouncement');
  const announcementKey = [progress.outcome, progress.current, progress.currentState, progress.failure].join('|');
  if (announcer && announcer.dataset.lastStage !== announcementKey) {
    announcer.dataset.lastStage = announcementKey;
    announcer.textContent = 'Mission ' + progress.current + '. Last completed: ' + progress.lastCompleted
      + (progress.failure === 'None' ? '.' : '. Last failure: ' + progress.failure + '.');
  }
  const summary = JSON.stringify(progress);
  if (root.dataset.snapshot === summary) return;
  root.dataset.snapshot = summary;
  const currentState = ['failed','interrupted','completed','current'].includes(progress.currentState)
    ? progress.currentState : 'idle';
  const steps = progress.items.map(item => {
    const cycle = item.cycle ? ` · cycle ${item.cycle}` : '';
    return `<li class="mission-progress-step" data-step-state="${item.state}"
      title="${escapeHtml(item.phase)}">
      <span class="mission-progress-marker" aria-hidden="true"></span>
      <span class="mission-progress-name">${escapeHtml(item.label)}</span>
      <span class="mission-progress-meta">${escapeHtml(item.state)}${escapeHtml(cycle)}</span>
    </li>`;
  }).join('');
  root.innerHTML = `
    <p class="mission-progress-disconnected" role="alert" hidden>Backend status unavailable. Progress below is the last confirmed snapshot, not live.</p>
    <div class="mission-progress-head">
      <h3>Mission progress</h3>
      <span class="mission-progress-outcome" data-outcome="${escapeHtml(progress.outcome)}">${escapeHtml(progress.outcome)}</span>
    </div>
    <div class="mission-progress-summary">
      <div class="mission-progress-reading" data-current-state="${currentState}">
        <span>Current step</span><strong>${escapeHtml(progress.current)}</strong>
      </div>
      <div class="mission-progress-reading">
        <span>Last completed</span><strong>${escapeHtml(progress.lastCompleted)}</strong>
      </div>
      <div class="mission-progress-reading" data-failure="${progress.failure === 'None' ? 'none' : 'present'}">
        <span>Last failure</span><strong>${escapeHtml(progress.failure)}</strong>
      </div>
    </div>
    <div class="mission-progress-context">
      <span>${escapeHtml(progress.detail)}</span>
      ${progress.arm && progress.arm !== '—' ? `<span>Arm: ${escapeHtml(progress.arm)}</span>` : ''}
    </div>
    <ol class="mission-progress-track" aria-label="Backend-observed stages">
      ${steps || '<li class="mission-progress-empty">No stage entered yet.</li>'}
    </ol>
  `;
}

function renderStatus(status) {
  const statusEl = document.getElementById('status');
  const camera = status.camera || {};
  const motor = status.motor_config || {};
  const motorStatus = status.motor_status || {};
  const pipeline = status.pipeline || {};
  const target = status.target_detection || {};
  const targetCenter = target.center || {};
  const targetBox = target.box || {};
  const deadbandRatio = Number(status.config?.drive?.target_x_deadband_ratio || 0.05);
  const armSequence = status.arm_sequence || {};
  const armStatus = status.arm_status || {};
  const armConfig = status.config?.arm || {};
  const stageTheme = status.stage_theme || {};
  const motionTheme = status.motion_theme || {};
  const armTheme = status.arm_theme || {};
  statusEl.innerHTML = `
    <div class="panel-chip-row">
      ${themeBadge(`Stage ${status.mission_state || status.phase || 'idle'}`, stageTheme)}
      ${themeBadge(`Motion ${status.intended_motion || 'idle'}`, motionTheme)}
      ${themeBadge(`Arm ${armSequence.state || 'idle'}`, armTheme)}
      <span class="theme-badge ${directionClass(motorStatus.vehicle_rotation)}">Rotation ${escapeHtml(motorRotationLabel(motorStatus))}</span>
    </div>
    <div class="status-grid stage-themed-grid" style="${escapeHtml(themeToCssVars(stageTheme))}">
      <div class="status-label">Running</div><div>${escapeHtml(status.running)}</div>
      <div class="status-label">Phase</div><div>${escapeHtml(status.phase)}</div>
      <div class="status-label">Detail</div><div>${escapeHtml(status.detail)}</div>
      <div class="status-label">Selected model</div><div>${escapeHtml(status.selected_model || 'none')}</div>
      <div class="status-label">Loaded model</div><div>${escapeHtml(status.loaded_model || 'none')}</div>
      <div class="status-label">AI backend</div><div>${escapeHtml(status.ai_ready)} | ${escapeHtml(status.ai_message || '')}</div>
      <div class="status-label">Pi pipeline FPS</div><div>${fmt(pipeline.fps || 0, 2)} fps | ${fmt(pipeline.cycle_time_ms || 0, 1)} ms/cycle</div>
      <div class="status-label">Camera</div><div>${escapeHtml(camera.backend || 'offline')} | live=${escapeHtml(camera.preview_live ?? false)} | camera_fps=${fmt(camera.fps || 0, 1)}</div>
      <div class="status-label">Mission state</div><div>${escapeHtml(status.mission_state || '-')}</div>
      <div class="status-label">Outcome</div><div>${escapeHtml(status.mission_outcome || '-')}</div>
      <div class="status-label">Failure reason</div><div>${escapeHtml(status.failure_reason || '-')} ${status.failure_stage ? `at ${escapeHtml(status.failure_stage)}` : ''}</div>
      <div class="status-label">Grip confirmation</div><div>${escapeHtml(status.grip_confirmation || 'not_sensor_confirmed')}</div>
      <div class="status-label">Mission report</div><div>${escapeHtml(status.mission_report_path ? 'Saved on Pi: ' + status.mission_report_path : 'Pending end of run')}</div>
      <div class="status-label">Pickup classes</div><div>${escapeHtml((status.pickup_classes || []).join('/'))}</div>
      <div class="status-label">Assumed held class (unverified)</div><div>${escapeHtml(status.held_class_id ?? '-')}</div>
      <div class="status-label">Drop-off class</div><div>${escapeHtml(status.dropoff_target_class_id ?? '-')}</div>
      <div class="status-label">Pickup lock</div><div>${escapeHtml(status.pickup_target_class_id ?? '-')}</div>
      <div class="status-label">Target found</div><div>${escapeHtml(status.target_found)}</div>
      <div class="status-label">Target side</div><div>${escapeHtml(status.target_side || '-')}</div>
      <div class="status-label">Car turn</div><div>${escapeHtml(status.car_turn_direction || '-')}</div>
      <div class="status-label">Intended motion</div><div>${escapeHtml(status.intended_motion || '-')}</div>
      <div class="status-label">Target center</div><div>x=${fmt(targetCenter.x, 1)} y=${fmt(targetCenter.y, 1)}</div>
      <div class="status-label">Target box</div><div>w=${fmt(targetBox.width, 1)} h=${fmt(targetBox.height, 1)}</div>
      <div class="status-label">Forward deadband</div><div>${fmt(deadbandRatio * 100, 1)}% of frame width</div>
      <div class="status-label">Saved grip trigger Y</div><div>${triggerGuidePercent(armConfig.grip_trigger_y_ratio ?? 0.3)}% (100=top, 0=bottom)</div>
      <div class="status-label">Saved drop-off trigger Y</div><div>${triggerGuidePercent(armConfig.dropoff_trigger_y_ratio ?? 0.3)}% (100=top, 0=bottom)</div>
      <div class="status-label">Backward after drop-off</div><div>${fmt(Number(status.config?.mission?.reverse_after_release_s || 0.9), 2)} s</div>
      <div class="status-label">Arm backend</div><div>enabled=${escapeHtml(armStatus.enabled ?? false)} | available=${escapeHtml(armStatus.available ?? false)} | ${escapeHtml(armStatus.backend || 'disabled')}</div>
      <div class="status-label">Arm sequence</div><div>${escapeHtml(armSequence.state || 'idle')} | ${escapeHtml(armSequence.note || '-')}</div>
      <div class="status-label">Arm pose map</div><div>start=#${escapeHtml(armConfig.roles?.starting_position ?? '-')} ready=#${escapeHtml(armConfig.roles?.grip_ready ?? '-')} grip=#${escapeHtml(armConfig.roles?.grip ?? '-')} lift=#${escapeHtml(armConfig.roles?.grip_and_lift ?? '-')} release=#${escapeHtml(armConfig.roles?.release ?? '-')}</div>
      <div class="status-label">Arm angles</div><div>servo0=${fmt(armStatus.servo0_angle, 0)} servo1=${fmt(armStatus.servo1_angle, 0)} servo2=${fmt(armStatus.servo2_angle ?? armStatus.grip_angle, 0)}</div>
      <div class="status-label">Command</div><div>left=${fmt(status.last_command?.left, 2)} right=${fmt(status.last_command?.right, 2)} note=${escapeHtml(status.last_command?.note || '')}</div>
      <div class="status-label">Motor GPIO</div><div>${escapeHtml(motor.gpio_available ?? false)}</div>
      <div class="status-label">Output summary</div><div>${escapeHtml(status.last_output_summary || '-')}</div>
      <div class="status-label">Arm status</div><div>${escapeHtml(armStatus.simulated ? 'Simulation mode active. ' : '')}${escapeHtml(armStatus.last_message || '-')}</div>
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

  renderMissionTimeline(status);
  renderArmPositionPanel(status);
  renderMotorPositionPanel(status);
  renderModelList(status);
  renderDetections(status);
  renderSummaryCards(status);
  renderViewer(status);
}


function triggerGuideY(ratio, height) {
  // Backend uses -H/2..+H/2 with 100%=top. SVG uses top-origin pixels.
  const parsed = Number(ratio);
  const clamped = Number.isFinite(parsed) ? Math.max(0, Math.min(1, parsed)) : 0.3;
  return Math.round(height * (1 - clamped));
}

function triggerGuidePercent(ratio) {
  const parsed = Number(ratio);
  // Backend persists 0.001 ratio units, equal to 0.1 percentage point.
  return Math.round((Number.isFinite(parsed) ? Math.max(0, Math.min(1, parsed)) : 0.3) * 1000) / 10;
}

function triggerGuideValues(status) {
  const arm = status.config?.arm || {};
  const savedGrip = triggerGuidePercent(arm.grip_trigger_y_ratio ?? 0.3);
  const savedDropoff = triggerGuidePercent(arm.dropoff_trigger_y_ratio ?? 0.3);
  const grip = triggerPreviewEdited
    ? clampTriggerPercent(document.getElementById('armGripYRatio')?.value)
    : savedGrip;
  const dropoff = triggerPreviewEdited
    ? clampTriggerPercent(document.getElementById('armDropoffYRatio')?.value)
    : savedDropoff;
  const preview = triggerPreviewEdited && (grip !== savedGrip || dropoff !== savedDropoff);
  return { grip, dropoff, savedGrip, savedDropoff, preview };
}

function renderTriggerReadout(guides) {
  const root = document.getElementById('triggerGuideReadout');
  if (!root) return;
  const grip = document.getElementById('triggerGripValue');
  const dropoff = document.getElementById('triggerDropoffValue');
  const status = document.getElementById('triggerGuideState');
  if (grip) grip.textContent = `Grip ${guides.grip}%`;
  if (dropoff) dropoff.textContent = `Drop-off ${guides.dropoff}%`;
  root.dataset.mode = guides.preview ? 'preview' : 'saved';
  if (status) {
    status.textContent = guides.preview
      ? `Preview only — server still uses Grip ${guides.savedGrip}%, Drop-off ${guides.savedDropoff}%. Save config to apply.`
      : 'Saved on server · 100% top / 50% middle / 0% bottom';
  }
}

function renderOverlay(status, guides = triggerGuideValues(status)) {
  const svg = document.getElementById('viewerOverlay');
  const frame = status.frame || {};
  const width = Math.max(1, Number(frame.width || 640));
  const height = Math.max(1, Number(frame.height || 360));
  const detections = status.detections || [];
  const deadbandRatio = Number(status.config?.drive?.target_x_deadband_ratio || 0.05);
  const deadbandWidth = width * deadbandRatio;
  const leftBand = width / 2 - deadbandWidth;
  const rightBand = width / 2 + deadbandWidth;
  const pickupY = triggerGuideY(guides.grip / 100, height);
  const dropoffY = triggerGuideY(guides.dropoff / 100, height);
  const pickupTextY = Math.max(12, Math.min(height - 5, pickupY - 6));
  const dropoffTextY = Math.max(12, Math.min(height - 5, dropoffY - 6));
  const scale = [100, 50, 0].map((pct) => {
    const y = triggerGuideY(pct / 100, height);
    const labelY = Math.max(14, Math.min(height - 6, y + 4));
    return `<line x1="43" y1="${y}" x2="55" y2="${y}" class="overlay-scale-tick" />
      <text x="39" y="${labelY}" text-anchor="end" class="overlay-scale-label">${pct}%</text>`;
  }).join('');

  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = '';

  const guideGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  guideGroup.setAttribute('class', 'overlay-guides');
  guideGroup.dataset.guideMode = guides.preview ? 'preview' : 'saved';
  guideGroup.innerHTML = `
    <rect x="${leftBand}" y="0" width="${rightBand - leftBand}" height="${height}" class="overlay-deadband" />
    <line x1="${width / 2}" y1="0" x2="${width / 2}" y2="${height}" class="overlay-axis" />
    <line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" class="overlay-axis" />
    <g class="overlay-frame-scale" aria-hidden="true">
      <rect x="0" y="0" width="59" height="${height}" class="overlay-scale-backdrop" />
      <line x1="49" y1="0" x2="49" y2="${height}" class="overlay-scale-spine" />
      ${scale}
    </g>
    <line x1="59" y1="${pickupY}" x2="${width}" y2="${pickupY}" class="overlay-trigger overlay-trigger-pickup" />
    <text x="68" y="${pickupTextY}" class="overlay-trigger-label overlay-trigger-pickup-label">Grip ${guides.grip}%</text>
    <line x1="59" y1="${dropoffY}" x2="${width}" y2="${dropoffY}" class="overlay-trigger overlay-trigger-dropoff" />
    <text x="${width - 8}" y="${dropoffTextY}" text-anchor="end" class="overlay-trigger-label overlay-trigger-dropoff-label">Drop-off ${guides.dropoff}%</text>
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
  const guides = triggerGuideValues(status);
  renderTriggerReadout(guides);
  const pipelineFps = fmt(status.pipeline?.fps || 0, 2);
  const detectionCount = String((status.detections || []).length);
  const serverAt = Number(status.server_status_at_ms);
  stats.title = Number.isFinite(serverAt) && serverAt > 0
    ? `Server status as of ${new Date(serverAt).toLocaleTimeString()} (server clock)`
    : 'Server status freshness unavailable';
  stats.innerHTML = `
    <span class="stat-pill">Objects ${escapeHtml(detectionCount)}</span>
    <span class="stat-pill">FPS ${escapeHtml(pipelineFps)}</span>
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.stage_theme || {}))}">State ${escapeHtml(status.mission_state || 'idle')}</span>
    <span class="stat-pill">Assumed held ${escapeHtml(status.held_class_id ?? '-')}</span>
    <span class="stat-pill">Target ${escapeHtml(status.target_side || 'none')}</span>
    <span class="stat-pill">Turn ${escapeHtml(status.car_turn_direction || 'stopped')}</span>
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.motion_theme || {}))}">Motion ${escapeHtml(status.intended_motion || 'idle')}</span>
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.arm_theme || {}))}">Arm ${escapeHtml(status.arm_sequence?.state || 'idle')}</span>
  `;

  if (liveFrameVisible) {
    video.style.display = 'block';
    svg.style.display = 'block';
    renderOverlay(status, guides);
    note.textContent = `Showing the Pi-generated annotated frame with a live mission-status overlay and a light guide overlay. Mission state: ${status.mission_state || 'idle'}. Intended motion: ${status.intended_motion || 'idle'}. Assumed held class (not sensor-confirmed): ${status.held_class_id ?? '-'}. Drop-off class: ${status.dropoff_target_class_id ?? '-'}. Target side: ${status.target_side || 'none'}. Car turn: ${status.car_turn_direction || 'stopped'}. Arm stage: ${status.arm_sequence?.state || 'idle'}.`;
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
    if (data.ok !== true || !data.config || !data.status) {
      throw new Error(data.message || 'Server did not confirm saved trigger settings.');
    }
    // Distinguish a successful HTTP/Save response from the effective Mission 1
    // status used by the runtime. The two independently returned values must agree.
    const savedArm = data.config.arm || {};
    const effectiveArm = data.status.config?.arm || {};
    for (const key of ['grip_trigger_y_ratio', 'dropoff_trigger_y_ratio']) {
      const saved = Number(savedArm[key]);
      const effective = Number(effectiveArm[key]);
      if (!Number.isFinite(saved) || !Number.isFinite(effective) || Math.abs(saved - effective) > 0.0001) {
        throw new Error(`Server readback disagrees on ${key}; trigger preview remains unsaved.`);
      }
    }
    triggerPreviewEdited = false; // only a server-confirmed save removes draft overlay
    populateConfig(data.config);
    currentStatus = data.status;
    renderStatus(data.status); // immediately show backend-applied marker positions
    setMessage('configMessage', data.message || 'Mission 1 config saved.');
    setMessage('armMessage', 'Arm trigger values confirmed by server.');
    await refresh();
    return true;
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to save config.', true);
    setMessage('armMessage', err.message || 'Failed to save Mission 1 arm pose config.', true);
    if (currentStatus) renderViewer(currentStatus); // retain clearly labelled unsaved preview
    return false;
  }
}

async function startMission() {
  try {
    if (!await saveConfig()) return; // never start a mission with unconfirmed trigger edits
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

async function rearmMission() {
  if (!window.confirm('Rearm mission safety at zero? This does not restart the mission.')) return;
  try {
    const result = await postJSON('/api/safety/rearm', { confirm: true });
    setMessage('configMessage', result.message || 'Mission fault rearmed.');
    await refresh();
  } catch (err) {
    setMessage('configMessage', err.message || 'Rearm failed.', true);
    await refresh();
  }
}

async function uploadModel() {
  const input = document.getElementById('modelUpload');
  const file = input.files && input.files[0];
  if (!file) {
    setMessage('modelMessage', 'Choose a .tflite file to upload to the Pi.', true);
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
    setMessage('modelMessage', 'No model selected. Upload a .tflite model, then choose it.', true);
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
    if (!await saveConfig()) return; // never move a servo after an unconfirmed config save
    const data = await postJSON('/api/arm/load_role', { role });
    setMessage('armMessage', data.message || `Loaded ${role} pose.`);
    await refresh();
  } catch (err) {
    setMessage('armMessage', err.message || `Failed to load ${role} pose.`, true);
  }
}


async function saveMotorConfig(payload) {
  try {
    const data = await postJSON('/api/motor/config', payload || {});
    if (data.status) {
      currentStatus = data.status;
      renderStatus(currentStatus);
    } else {
      await refresh();
    }
    setMessage('motorMessage', data.message || 'Mission 1 motor calibration saved.');
  } catch (err) {
    setMessage('motorMessage', err.message || 'Failed to save Mission 1 motor calibration.', true);
  }
}


async function refresh() {
  if (document.hidden) {
    scheduleRefresh(); // no background HTTP status reads
    return;
  }
  if (refreshInFlight) return;
  refreshInFlight = true;
  try {
    const status = await fetchJSON('/api/status');
    statusFailures = 0;
    currentStatus = status;
    renderStatus(status);
  } catch (err) {
    statusFailures = Math.min(4, statusFailures + 1);
    setMessage('configMessage', err.message || 'Cannot refresh Mission 1. Check the Pi connection, then Refresh.', true);
    const progressRoot = document.getElementById('missionTimeline');
    if (progressRoot) {
      progressRoot.dataset.connection = 'disconnected';
      const warning = progressRoot.querySelector('.mission-progress-disconnected');
      if (warning) warning.hidden = false;
    }
  } finally {
    refreshInFlight = false;
    scheduleRefresh();
  }
}

function refreshFrame() {
  if (document.hidden) {
    scheduleFrameRefresh();
    return;
  }
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
  let timeoutId = null;
  const finish = (success = true) => {
    if (requestId !== latestFrameRequestId || !frameRequestInFlight) return;
    frameRequestInFlight = false;
    frameFailures = success ? 0 : Math.min(4, frameFailures + 1);
    if (timeoutId !== null) window.clearTimeout(timeoutId);
    scheduleFrameRefresh(); // one request at a time; no recurring overlap
  };
  video.onload = () => finish(true);
  video.onerror = () => finish(false);
  video.src = `/api/frame.jpg?t=${Date.now()}`;
  timeoutId = window.setTimeout(() => {
    if (requestId === latestFrameRequestId && frameRequestInFlight) {
      // Abandon a stalled image load rather than issuing overlapping requests.
      video.removeAttribute('src');
      finish(false);
    }
  }, Math.max(1000, FRAME_REFRESH_MS * 4));
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
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      const video = document.getElementById('videoFeed');
      ++latestFrameRequestId;
      frameRequestInFlight = false;
      if (video) video.removeAttribute('src');
      scheduleRefresh(); // no HTTP while hidden; do not change mission motor safety
      scheduleFrameRefresh();
    } else {
      statusFailures = 0;
      frameFailures = 0;
      scheduleRefresh(0);
      scheduleFrameRefresh(0);
    }
  });
}

document.getElementById('saveConfigBtn').onclick = saveConfig;
for (const id of ['armGripYRatio', 'armDropoffYRatio']) {
  document.getElementById(id)?.addEventListener('input', () => {
    triggerPreviewEdited = true;
    if (currentStatus) renderViewer(currentStatus); // visual only; no POST or motor command
  });
}
document.getElementById('startBtn').onclick = startMission;
document.getElementById('stopBtn').onclick = stopMission;
document.getElementById('rearmBtn').onclick = rearmMission;
document.getElementById('uploadModelBtn').onclick = uploadModel;
document.getElementById('loadModelBtn').onclick = loadSelectedModel;
document.querySelectorAll('.arm-load-role').forEach((button) => {
  button.onclick = () => loadArmRole(String(button.dataset.role || ''));
});

init();
