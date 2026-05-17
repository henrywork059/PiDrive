const initialStatus = JSON.parse(document.getElementById('mainDashboardInitialStatus')?.textContent || '{}');
const globalCode = document.getElementById('mdGlobalCode');
const statusJson = document.getElementById('mdStatusJson');
const errorJson = document.getElementById('mdErrorJson');
const actionLog = document.getElementById('mdActionLog');
const cameraPreview = document.getElementById('mdCameraPreview');
const previewFrame = document.getElementById('mdPreviewFrame');
const overlayToggle = document.getElementById('mdOverlayToggle');
const overlayMode = document.getElementById('mdOverlayMode');
const overlayCar = document.getElementById('mdOverlayCar');
const overlayPath = document.getElementById('mdOverlayPath');
const overlayThrottleFill = document.getElementById('mdOverlayThrottleFill');
const overlaySteeringFill = document.getElementById('mdOverlaySteeringFill');
const overlayThrottleValue = document.getElementById('mdOverlayThrottleValue');
const overlaySteeringValue = document.getElementById('mdOverlaySteeringValue');
const overlayLeftValue = document.getElementById('mdOverlayLeftValue');
const overlayRightValue = document.getElementById('mdOverlayRightValue');
const motorArm = document.getElementById('mdMotorArm');
const manualSpeed = document.getElementById('mdManualSpeed');
const manualSpeedValue = document.getElementById('mdManualSpeedValue');
const manualSafetyText = document.getElementById('mdManualSafetyText');
const driveButtons = Array.from(document.querySelectorAll('.md-drive-button[data-steering]'));
const channelSubmit = document.querySelector('#mdMotorChannelForm button[type="submit"]');

function isOkCode(code) {
  return String(code || '').startsWith('PISD-OK');
}

function setCode(element, code) {
  if (!element) return;
  const value = code || 'PISD-OK-000';
  element.textContent = value;
  element.dataset.state = isOkCode(value) ? 'ok' : 'error';
}

function setPanelCode(panelName, code) {
  setCode(document.querySelector(`[data-code-for="${panelName}"]`), code);
}



function clampUnit(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return 0;
  return Math.max(-1, Math.min(1, number));
}

function signedText(value) {
  const number = clampUnit(value);
  return `${number >= 0 ? '+' : ''}${number.toFixed(2)}`;
}

function setSignedFill(element, value) {
  if (!element) return;
  const number = clampUnit(value);
  element.style.left = number < 0 ? `${50 + (number * 50)}%` : '50%';
  element.style.width = `${Math.abs(number) * 50}%`;
}

function driveModeText(throttle, steering) {
  const throttleAbs = Math.abs(throttle);
  const steeringAbs = Math.abs(steering);
  if (throttleAbs < 0.02 && steeringAbs < 0.02) return 'STOPPED';
  const direction = throttle < -0.02 ? 'REV' : throttle > 0.02 ? 'FWD' : 'TURN';
  if (steeringAbs < 0.08) return direction;
  return `${direction} ${steering < 0 ? 'LEFT' : 'RIGHT'}`;
}

function drawIntendedPath(throttle, steering) {
  if (!overlayPath) return;
  const speed = Math.abs(throttle);
  const steeringAbs = Math.abs(steering);
  const moving = speed >= 0.02;
  const isReverse = throttle < -0.02;
  const travel = 28 + (speed * 48);
  const startX = 50;
  const startY = isReverse ? 73 : 86;
  const endY = isReverse ? Math.min(98, startY + travel * 0.42) : Math.max(10, startY - travel);
  const reverseSteerFactor = isReverse ? -1 : 1;
  const controlX = 50 + (steering * reverseSteerFactor * (22 + steeringAbs * 34));
  const endX = 50 + (steering * reverseSteerFactor * (12 + steeringAbs * 30));
  const controlY = isReverse ? (startY + endY) / 2 + 8 : (startY + endY) / 2 - 10;

  overlayPath.setAttribute('d', `M ${startX.toFixed(1)} ${startY.toFixed(1)} Q ${controlX.toFixed(1)} ${controlY.toFixed(1)} ${endX.toFixed(1)} ${endY.toFixed(1)}`);
  overlayPath.style.opacity = moving || steeringAbs >= 0.02 ? '0.86' : '0.28';
  overlayPath.style.strokeWidth = String(2.2 + speed * 3.8);
  overlayPath.style.strokeDasharray = isReverse ? '5 4' : 'none';
}

function updateDriveOverlay(source = {}) {
  const command = source.last_command || source.command || source;
  const throttle = clampUnit(command.throttle ?? source.throttle ?? 0);
  const steering = clampUnit(command.steering ?? source.steering ?? 0);
  const left = clampUnit(source.last_left ?? source.left ?? 0);
  const right = clampUnit(source.last_right ?? source.right ?? 0);
  const turnDeg = steering * 28;
  const moving = Math.abs(throttle) >= 0.02;

  if (overlayMode) overlayMode.textContent = driveModeText(throttle, steering);
  if (overlayThrottleValue) overlayThrottleValue.textContent = signedText(throttle);
  if (overlaySteeringValue) overlaySteeringValue.textContent = signedText(steering);
  if (overlayLeftValue) overlayLeftValue.textContent = signedText(left);
  if (overlayRightValue) overlayRightValue.textContent = signedText(right);
  setSignedFill(overlayThrottleFill, throttle);
  setSignedFill(overlaySteeringFill, steering);
  if (overlayCar) {
    overlayCar.style.transform = `translateX(-50%) rotate(${turnDeg}deg)`;
    overlayCar.style.opacity = moving || Math.abs(steering) >= 0.02 ? '1' : '0.78';
  }
  drawIntendedPath(throttle, steering);
}

function setOverlayEnabled(enabled) {
  if (!previewFrame || !overlayToggle) return;
  previewFrame.classList.toggle('md-overlay-enabled', enabled);
  overlayToggle.textContent = enabled ? 'Overlay on' : 'Overlay off';
  overlayToggle.setAttribute('aria-pressed', enabled ? 'true' : 'false');
}

function logAction(label, payload, httpStatus = '') {
  const code = payload?.code || (httpStatus && httpStatus >= 400 ? 'PISD-API-002' : 'PISD-OK-000');
  setCode(globalCode, code);
  setPanelCode('action-log', code);
  actionLog.textContent = JSON.stringify({ action: label, http_status: httpStatus, response: payload }, null, 2);
}

async function apiCall(method, path, body = undefined, panelName = 'action-log') {
  const options = { method, headers: {} };
  if (body !== undefined && method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const contentType = response.headers.get('content-type') || '';
  let payload;
  if (contentType.includes('application/json')) {
    payload = await response.json();
  } else {
    const blob = await response.blob();
    payload = { ok: response.ok, code: response.ok ? 'PISD-OK-000' : 'PISD-API-002', content_type: contentType, bytes: blob.size };
  }
  setPanelCode(panelName, payload.code);
  logAction(`${method} ${path}`, payload, response.status);
  return { response, payload };
}

function renderStatus(status) {
  if (!status) return;
  document.getElementById('mdVersion').textContent = status.version || '-';
  document.getElementById('mdHardware').textContent = status.hardware_requested ? 'hardware' : 'simulation';
  document.getElementById('mdCameraState').textContent = `${status.camera?.backend || 'unknown'} / ${status.camera?.running ? 'running' : 'stopped'}`;
  document.getElementById('mdMotorState').textContent = `${status.motor?.adapter || 'unknown'} / ${status.motor?.hardware_enabled ? 'hardware' : 'simulation'}`;
  statusJson.textContent = JSON.stringify(status, null, 2);
  setPanelCode('system-status', status.code || 'PISD-OK-000');
  setCode(globalCode, status.code || 'PISD-OK-000');
  updateDriveOverlay(status.motor || {});
}

async function refreshStatus() {
  try {
    const { payload } = await apiCall('GET', '/api/status', undefined, 'system-status');
    renderStatus(payload);
  } catch (error) {
    logAction('refreshStatus', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

// PiSD_0_4_1 cleanup:
// The old dashboard snapshot-refresh helper is intentionally kept commented out
// because the current dashboard preview uses the MJPEG live stream path only.
// Re-enable this only if a future dashboard snapshot-mode button is restored.
// function refreshFrame() {
//   cameraPreview.dataset.mode = 'snapshot';
//   cameraPreview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
// }

function startLivePreview() {
  cameraPreview.dataset.mode = 'mjpeg';
  cameraPreview.src = `/video_feed?t=${Date.now()}`;
}

async function stopAll(panelName = 'safety-stop') {
  try {
    const { payload } = await apiCall('POST', '/api/control/stop', {}, panelName);
    updateDriveOverlay(payload.motor || { steering: 0, throttle: 0, left: 0, right: 0 });
    await refreshStatus();
  } catch (error) {
    logAction('stopAll', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

function updateMotorLock() {
  const armed = motorArm.checked;
  driveButtons.forEach((button) => { button.disabled = !armed; });
  if (channelSubmit) channelSubmit.disabled = !armed;
  manualSafetyText.textContent = armed
    ? 'Motor output is armed. Keep wheels lifted. STOP remains active.'
    : 'Movement buttons are locked until the safety checkbox is enabled. STOP remains active.';
}

function manualPayloadFromButton(button) {
  const speed = Number(manualSpeed.value || 0.18);
  const baseThrottle = Number(button.dataset.throttle || 0);
  const steering = Number(button.dataset.steering || 0);
  const throttle = baseThrottle === 0 ? 0 : Math.sign(baseThrottle) * speed;
  return { steering, throttle, steer_mix: 1.0 };
}

async function sendManual(button) {
  if (!motorArm.checked) {
    const payload = { ok: false, code: 'PISD-MOT-008', message: 'Manual drive refused by dashboard because motor output is not armed.' };
    setPanelCode('manual-drive', payload.code);
    logAction('manual drive blocked', payload, 0);
    return;
  }
  try {
    const intent = manualPayloadFromButton(button);
    updateDriveOverlay(intent);
    const { payload } = await apiCall('POST', '/api/control/manual', intent, 'manual-drive');
    updateDriveOverlay(payload.motor || payload || intent);
  } catch (error) {
    logAction('manual drive', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

function formToPayload(form) {
  const data = {};
  for (const element of form.elements) {
    if (!element.name) continue;
    if (element.type === 'checkbox') data[element.name] = element.checked;
    else if (element.type === 'number' || ['direction', 'speed', 'duration'].includes(element.name)) data[element.name] = Number(element.value);
    else data[element.name] = element.value;
  }
  return data;
}

async function sendChannelTest(event) {
  event.preventDefault();
  if (!motorArm.checked) {
    const payload = { ok: false, code: 'PISD-MOT-008', message: 'Motor channel test refused by dashboard because motor output is not armed.' };
    setPanelCode('motor-channel-calibration', payload.code);
    logAction('motor channel blocked', payload, 0);
    return;
  }
  const payload = formToPayload(event.currentTarget);
  payload.enable_motor_output = true;
  try {
    await apiCall('POST', '/api/motor/test-channel', payload, 'motor-channel-calibration');
  } catch (error) {
    logAction('motor channel test', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

async function readErrors() {
  try {
    const { payload } = await apiCall('GET', '/api/errors', undefined, 'error-monitor');
    errorJson.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    errorJson.textContent = JSON.stringify({ ok: false, code: 'PISD-API-002', message: String(error) }, null, 2);
  }
}

async function clearErrors() {
  try {
    const { payload } = await apiCall('POST', '/api/errors/clear', {}, 'error-monitor');
    errorJson.textContent = JSON.stringify(payload, null, 2);
  } catch (error) {
    errorJson.textContent = JSON.stringify({ ok: false, code: 'PISD-API-002', message: String(error) }, null, 2);
  }
}

function bindEvents() {
  document.getElementById('mdRefreshStatus').addEventListener('click', refreshStatus);
  document.getElementById('mdCameraStart').addEventListener('click', async () => {
    await apiCall('POST', '/api/camera/start', {}, 'camera-preview');
    startLivePreview();
    await refreshStatus();
  });
  document.getElementById('mdCameraStop').addEventListener('click', async () => {
    await apiCall('POST', '/api/camera/stop', {}, 'camera-preview');
    await refreshStatus();
  });
  document.getElementById('mdCameraRefresh').addEventListener('click', startLivePreview);
  if (overlayToggle) overlayToggle.addEventListener('click', () => setOverlayEnabled(!previewFrame.classList.contains('md-overlay-enabled')));
  document.getElementById('mdStopAllTop').addEventListener('click', () => stopAll('safety-stop'));
  document.getElementById('mdStopAllCenter').addEventListener('click', () => stopAll('manual-drive'));
  document.getElementById('mdStopAllPanel').addEventListener('click', () => stopAll('safety-stop'));
  document.getElementById('mdReadErrors').addEventListener('click', readErrors);
  document.getElementById('mdClearErrors').addEventListener('click', clearErrors);
  document.getElementById('mdMotorChannelForm').addEventListener('submit', sendChannelTest);
  motorArm.addEventListener('change', updateMotorLock);
  manualSpeed.addEventListener('input', () => { manualSpeedValue.textContent = Number(manualSpeed.value).toFixed(2); });
  driveButtons.forEach((button) => button.addEventListener('click', () => sendManual(button)));
}

renderStatus(initialStatus);
bindEvents();
updateMotorLock();
setOverlayEnabled(true);
updateDriveOverlay(initialStatus.motor || {});
