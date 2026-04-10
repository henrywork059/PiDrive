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
  document.getElementById('armGripYRatio').value = fmtShort((Number(armConfig?.grip_trigger_y_ratio ?? 0.30) || 0) * 100, 0);
  document.getElementById('armDropoffYRatio').value = fmtShort((Number(armConfig?.dropoff_trigger_y_ratio ?? 0.30) || 0) * 100, 0);
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
    grip_trigger_y_ratio: Number(document.getElementById('armGripYRatio').value || 30) / 100,
    dropoff_trigger_y_ratio: Number(document.getElementById('armDropoffYRatio').value || 30) / 100,
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
  const stageTheme = status.stage_theme || {};
  const motionTheme = status.motion_theme || {};
  const armTheme = status.arm_theme || {};
  const items = [
    { label: 'Phase', value: status.phase || 'idle', theme: stageTheme },
    { label: 'Mission state', value: status.mission_state || '-', theme: stageTheme },
    { label: 'Objects', value: String(detections.length), theme: stageTheme },
    { label: 'Target side', value: status.target_side || '-', theme: motionTheme },
    { label: 'Holding', value: status.held_class_id ?? '-', theme: armTheme },
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
      <div class="status-label">Pickup classes</div><div>${escapeHtml((status.pickup_classes || []).join('/'))}</div>
      <div class="status-label">Holding class</div><div>${escapeHtml(status.held_class_id ?? '-')}</div>
      <div class="status-label">Drop-off class</div><div>${escapeHtml(status.dropoff_target_class_id ?? '-')}</div>
      <div class="status-label">Pickup lock</div><div>${escapeHtml(status.pickup_target_class_id ?? '-')}</div>
      <div class="status-label">Target found</div><div>${escapeHtml(status.target_found)}</div>
      <div class="status-label">Target side</div><div>${escapeHtml(status.target_side || '-')}</div>
      <div class="status-label">Car turn</div><div>${escapeHtml(status.car_turn_direction || '-')}</div>
      <div class="status-label">Intended motion</div><div>${escapeHtml(status.intended_motion || '-')}</div>
      <div class="status-label">Target center</div><div>x=${fmt(targetCenter.x, 1)} y=${fmt(targetCenter.y, 1)}</div>
      <div class="status-label">Target box</div><div>w=${fmt(targetBox.width, 1)} h=${fmt(targetBox.height, 1)}</div>
      <div class="status-label">Forward deadband</div><div>${fmt(deadbandRatio * 100, 1)}% of frame width</div>
      <div class="status-label">Grip trigger Y</div><div>${fmt((Number(armConfig.grip_trigger_y_ratio || 0) * 100), 0)}% (100=top, 0=bottom)</div>
      <div class="status-label">Drop-off trigger Y</div><div>${fmt((Number(armConfig.dropoff_trigger_y_ratio || 0) * 100), 0)}% (100=top, 0=bottom)</div>
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

  renderArmPositionPanel(status);
  renderMotorPositionPanel(status);
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
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.stage_theme || {}))}">State ${escapeHtml(status.mission_state || 'idle')}</span>
    <span class="stat-pill">Holding ${escapeHtml(status.held_class_id ?? '-')}</span>
    <span class="stat-pill">Target ${escapeHtml(status.target_side || 'none')}</span>
    <span class="stat-pill">Turn ${escapeHtml(status.car_turn_direction || 'stopped')}</span>
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.motion_theme || {}))}">Motion ${escapeHtml(status.intended_motion || 'idle')}</span>
    <span class="stat-pill themed-pill" style="${escapeHtml(themeToCssVars(status.arm_theme || {}))}">Arm ${escapeHtml(status.arm_sequence?.state || 'idle')}</span>
  `;

  if (liveFrameVisible) {
    video.style.display = 'block';
    svg.style.display = 'block';
    renderOverlay(status);
    note.textContent = `Showing the Pi-generated annotated frame with a live mission-status overlay and a light guide overlay. Mission state: ${status.mission_state || 'idle'}. Intended motion: ${status.intended_motion || 'idle'}. Holding class: ${status.held_class_id ?? '-'}. Drop-off class: ${status.dropoff_target_class_id ?? '-'}. Target side: ${status.target_side || 'none'}. Car turn: ${status.car_turn_direction || 'stopped'}. Arm stage: ${status.arm_sequence?.state || 'idle'}.`;
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
