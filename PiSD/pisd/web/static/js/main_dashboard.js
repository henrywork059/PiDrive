const initialStatus = JSON.parse(document.getElementById('mainDashboardInitialStatus')?.textContent || '{}');
const globalCode = document.getElementById('mdGlobalCode');
const statusJson = document.getElementById('mdStatusJson');
const errorJson = document.getElementById('mdErrorJson');
const actionLog = document.getElementById('mdActionLog');
const cameraPreview = document.getElementById('mdCameraPreview');
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
}

async function refreshStatus() {
  try {
    const { payload } = await apiCall('GET', '/api/status', undefined, 'system-status');
    renderStatus(payload);
  } catch (error) {
    logAction('refreshStatus', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

function refreshFrame() {
  cameraPreview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
}

async function stopAll(panelName = 'safety-stop') {
  try {
    await apiCall('POST', '/api/control/stop', {}, panelName);
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
    await apiCall('POST', '/api/control/manual', manualPayloadFromButton(button), 'manual-drive');
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
    refreshFrame();
    await refreshStatus();
  });
  document.getElementById('mdCameraStop').addEventListener('click', async () => {
    await apiCall('POST', '/api/camera/stop', {}, 'camera-preview');
    await refreshStatus();
  });
  document.getElementById('mdCameraRefresh').addEventListener('click', refreshFrame);
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
