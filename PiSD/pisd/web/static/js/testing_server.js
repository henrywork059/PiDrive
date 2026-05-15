const initialStatus = JSON.parse(document.getElementById('initialStatusJson').textContent || '{}');
const manifest = JSON.parse(document.getElementById('manifestJson').textContent || '{}');

const lastResponse = document.getElementById('lastResponse');
const statusPanel = document.getElementById('statusPanel');
const globalCode = document.getElementById('globalCode');
const preview = document.getElementById('cameraPreview');

function setCode(code) {
  const value = code || 'PISD-OK-000';
  globalCode.textContent = value;
  globalCode.classList.toggle('fail', value.includes('-API-') || value.includes('-CAM-') || value.includes('-MOT-') || value.includes('-APP-'));
  globalCode.classList.toggle('warn', value.includes('-TEST-'));
}

function showResponse(label, payload, httpStatus = null) {
  const data = { label, http_status: httpStatus, response: payload };
  lastResponse.textContent = JSON.stringify(data, null, 2);
  if (payload && payload.code) setCode(payload.code);
}

function formToJson(form) {
  const payload = {};
  for (const element of form.elements) {
    if (!element.name) continue;
    if (element.type === 'checkbox') {
      payload[element.name] = element.checked;
      continue;
    }
    let value = element.value;
    const declared = element.dataset.type;
    if (declared === 'boolean') value = value === 'true';
    else if (declared === 'number' || element.type === 'number') value = Number(value);
    payload[element.name] = value;
  }
  return payload;
}

async function apiCall(method, path, body = undefined) {
  const options = { method, headers: {} };
  if (body !== undefined && method !== 'GET') {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  const contentType = response.headers.get('content-type') || '';
  let payload;
  if (contentType.includes('application/json')) payload = await response.json();
  else payload = { ok: response.ok, code: response.ok ? 'PISD-OK-000' : 'PISD-API-002', content_type: contentType, bytes: (await response.blob()).size };
  showResponse(`${method} ${path}`, payload, response.status);
  return { response, payload };
}

async function refreshStatus() {
  try {
    const { payload } = await apiCall('GET', '/api/status');
    statusPanel.textContent = JSON.stringify(payload, null, 2);
    setCode(payload.code || 'PISD-OK-000');
  } catch (error) {
    showResponse('refreshStatus', { ok: false, code: 'PISD-API-002', message: String(error) });
  }
}

function refreshFrame() {
  preview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
}

function buildManifest() {
  const box = document.getElementById('manifestList');
  box.innerHTML = '';
  for (const endpoint of manifest.endpoints || []) {
    const chip = document.createElement('div');
    chip.className = 'endpoint-chip';
    chip.innerHTML = `<strong>${endpoint.method} ${endpoint.path}</strong><small>${endpoint.purpose || ''}</small>`;
    chip.addEventListener('click', () => {
      document.getElementById('customMethod').value = endpoint.method;
      document.getElementById('customPath').value = endpoint.path;
    });
    box.appendChild(chip);
  }
}



function smokeLine(ok, code, label, message) {
  const state = ok ? 'OK  ' : 'FAIL';
  return `${state} ${String(code || 'PISD-API-002').padEnd(13)} ${label} - ${message}`;
}

async function runSafeSmokeTest() {
  const panel = document.getElementById('smokeTestPanel');
  const lines = [];
  panel.textContent = 'Running safe browser smoke test...';

  async function step(label, method, path, body, accept) {
    try {
      const { response, payload } = await apiCall(method, path, body);
      const code = payload && payload.code ? payload.code : (response.ok ? 'PISD-OK-000' : 'PISD-API-002');
      const accepted = accept ? accept(response, payload, code) : response.ok;
      lines.push(smokeLine(accepted, code, label, accepted ? 'passed' : `unexpected HTTP ${response.status}`));
      panel.textContent = lines.join('\n');
      return { ok: accepted, response, payload, code };
    } catch (error) {
      lines.push(smokeLine(false, 'PISD-API-002', label, String(error)));
      panel.textContent = lines.join('\n');
      return { ok: false, error };
    }
  }

  await step('api.status', 'GET', '/api/status', undefined, (_r, payload) => payload.code === 'PISD-OK-000');
  await step('api.test_gui.manifest', 'GET', '/api/test-gui/manifest', undefined, (_r, payload) => payload.code === 'PISD-OK-000' && Array.isArray(payload.endpoints));
  await step('api.camera.start', 'POST', '/api/camera/start', {}, (_r, payload) => payload.ok === true && payload.code === 'PISD-OK-000');
  await step('api.camera.config', 'GET', '/api/camera/config', undefined, (_r, payload) => payload.code === 'PISD-OK-000' && payload.config);
  await step('api.camera.frame', 'GET', '/api/camera/frame.jpg', undefined, (_r, payload) => payload.code === 'PISD-OK-000' && payload.bytes > 0);
  await step('api.camera.apply_safe', 'POST', '/api/camera/apply', {
    width: 426,
    height: 240,
    fps: 12,
    preview_quality: 65,
    capture_source: 'request',
    array_color_order: 'rgb',
    buffer_count: 3,
    queue: false
  }, (_r, payload) => payload.ok === true && payload.code === 'PISD-OK-000');
  await step('api.motor.config', 'GET', '/api/motor/config', undefined, (_r, payload) => payload.code === 'PISD-OK-000' && payload.config);
  await step('api.motor.apply_safe', 'POST', '/api/motor/apply', formToJson(document.getElementById('motorSettingsForm')), (_r, payload) => payload.code === 'PISD-OK-000');
  await step('api.motor.test_channel_unarmed', 'POST', '/api/motor/test-channel', {
    side: 'left',
    direction: 1,
    speed: 0.02,
    duration: 0.05,
    enable_motor_output: false
  }, (response, payload) => (response.status === 200 && payload.code === 'PISD-OK-000') || (response.status === 403 && payload.code === 'PISD-MOT-008'));
  await step('api.control.stop', 'POST', '/api/control/stop', {}, (_r, payload) => payload.code === 'PISD-OK-000');
  await refreshStatus();
  refreshFrame();

  const failed = lines.filter((line) => line.startsWith('FAIL')).length;
  lines.push('------------------------------------------------------------------------');
  lines.push(smokeLine(failed === 0, failed === 0 ? 'PISD-OK-000' : 'PISD-TEST-011', 'browser.smoke_summary', `failed=${failed}`));
  panel.textContent = lines.join('\n');
}

document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-call]');
  if (!target) return;
  const call = JSON.parse(target.dataset.call);
  await apiCall(call.method, call.path, call.body || undefined);
  if (call.path.includes('/camera/start') || call.path.includes('/camera/stop') || call.path.includes('/control/stop')) {
    await refreshStatus();
  }
});

document.getElementById('refreshStatusBtn').addEventListener('click', refreshStatus);
document.getElementById('refreshFrameBtn').addEventListener('click', refreshFrame);
document.getElementById('runSmokeTestBtn').addEventListener('click', runSafeSmokeTest);
document.getElementById('runSmokeTestBtn2').addEventListener('click', runSafeSmokeTest);
document.getElementById('stopAllBtn').addEventListener('click', async () => {
  await apiCall('POST', '/api/control/stop', {});
  await refreshStatus();
});
document.getElementById('applyCameraBtn').addEventListener('click', async () => {
  const payload = formToJson(document.getElementById('cameraSettingsForm'));
  await apiCall('POST', '/api/camera/apply', payload);
  refreshFrame();
  await refreshStatus();
});
document.getElementById('applyMotorBtn').addEventListener('click', async () => {
  const payload = formToJson(document.getElementById('motorSettingsForm'));
  await apiCall('POST', '/api/motor/apply', payload);
  await refreshStatus();
});
document.getElementById('testMotorBtn').addEventListener('click', async () => {
  const payload = formToJson(document.getElementById('motorChannelForm'));
  await apiCall('POST', '/api/motor/test-channel', payload);
  await refreshStatus();
});
document.getElementById('customSendBtn').addEventListener('click', async () => {
  const method = document.getElementById('customMethod').value;
  const path = document.getElementById('customPath').value.trim() || '/api/status';
  let body;
  if (method !== 'GET') {
    try { body = JSON.parse(document.getElementById('customBody').value || '{}'); }
    catch (error) { showResponse('custom JSON parse', { ok: false, code: 'PISD-API-001', message: String(error) }); return; }
  }
  await apiCall(method, path, body);
  if (path.includes('/camera/frame')) refreshFrame();
});

buildManifest();
statusPanel.textContent = JSON.stringify(initialStatus, null, 2);
setCode(initialStatus.code || 'PISD-OK-000');
setInterval(refreshFrame, 1500);
setInterval(refreshStatus, 3000);
