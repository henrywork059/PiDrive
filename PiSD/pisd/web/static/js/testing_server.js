const initialStatus = JSON.parse(document.getElementById('initialStatusJson').textContent || '{}');
const manifest = JSON.parse(document.getElementById('manifestJson').textContent || '{}');

const lastResponse = document.getElementById('lastResponse');
const statusPanel = document.getElementById('statusPanel');
const globalCode = document.getElementById('globalCode');
const preview = document.getElementById('cameraPreview');
const fpsCode = document.getElementById('fpsCode');
const fpsPanel = document.getElementById('fpsTestPanel');

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
  preview.dataset.mode = 'snapshot';
  preview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
}

function startLivePreview() {
  preview.dataset.mode = 'mjpeg';
  preview.src = `/video_feed?t=${Date.now()}`;
}

async function startCameraAndLivePreview() {
  await apiCall('POST', '/api/camera/start', {});
  startLivePreview();
  await refreshStatus();
}

function setFpsCode(code) {
  if (!fpsCode) return;
  fpsCode.textContent = code || 'PISD-OK-000';
  fpsCode.classList.toggle('fail', !String(fpsCode.textContent).startsWith('PISD-OK'));
}

function fastPreviewPayload() {
  return {
    width: Number(document.getElementById('fpsPresetWidth')?.value || 426),
    height: Number(document.getElementById('fpsPresetHeight')?.value || 240),
    fps: Number(document.getElementById('fpsPresetFps')?.value || 30),
    preview_quality: Number(document.getElementById('fpsPresetQuality')?.value || 50),
    capture_source: 'array',
    array_color_order: 'rgb',
    buffer_count: 4,
    queue: true
  };
}

async function readFpsStats(label = 'api.camera.fps_stats') {
  const { response, payload } = await apiCall('GET', '/api/camera/fps-stats');
  setFpsCode(payload.code || (response.ok ? 'PISD-OK-000' : 'PISD-API-002'));
  if (fpsPanel) {
    fpsPanel.textContent = JSON.stringify({ label, http_status: response.status, response: payload }, null, 2);
  }
  return payload;
}

async function applyFastPreviewPreset() {
  const payload = fastPreviewPayload();
  const result = await apiCall('POST', '/api/camera/apply', payload);
  setFpsCode(result.payload.code || (result.response.ok ? 'PISD-OK-000' : 'PISD-API-002'));
  startLivePreview();
  await refreshStatus();
  return result.payload;
}

async function runMaxFpsTest() {
  const seconds = Math.max(2, Number(document.getElementById('fpsTestSeconds')?.value || 5));
  const applyPreset = Boolean(document.getElementById('fpsApplyFastPreset')?.checked);
  const lines = [];
  const startedAt = performance.now();
  let frames = 0;
  let bytes = 0;
  let failed = 0;
  if (fpsPanel) fpsPanel.textContent = 'Running max FPS test...';
  try {
    await apiCall('POST', '/api/camera/start', {});
    if (applyPreset) {
      await applyFastPreviewPreset();
      lines.push(`OK   PISD-OK-000   fps.fast_preset - ${JSON.stringify(fastPreviewPayload())}`);
    } else {
      startLivePreview();
    }
    const before = await readFpsStats('fps.before');
    const endAt = performance.now() + seconds * 1000;
    while (performance.now() < endAt) {
      try {
        const response = await fetch(`/api/camera/frame.jpg?fpsTest=${Date.now()}-${frames}`, { cache: 'no-store' });
        const blob = await response.blob();
        if (response.ok && blob.size > 0) {
          frames += 1;
          bytes += blob.size;
        } else {
          failed += 1;
        }
      } catch (_error) {
        failed += 1;
      }
      if (frames % 5 === 0 && fpsPanel) {
        const elapsed = Math.max(0.001, (performance.now() - startedAt) / 1000);
        fpsPanel.textContent = `running... snapshot_fetch_frames=${frames} client_fetch_fps=${(frames / elapsed).toFixed(2)} failed=${failed}`;
      }
    }
    const elapsed = Math.max(0.001, (performance.now() - startedAt) / 1000);
    const after = await readFpsStats('fps.after');
    const code = failed === 0 ? 'PISD-OK-000' : 'PISD-TEST-017';
    setFpsCode(code);
    lines.push(`${failed === 0 ? 'OK  ' : 'FAIL'} ${code}   fps.client_snapshot_fetch - frames=${frames} fps=${(frames / elapsed).toFixed(2)} bytes=${bytes} failed=${failed}`);
    lines.push(`OK   PISD-OK-000   fps.backend_capture - measured=${after.stats?.measured_capture_fps ?? 'n/a'} target=${after.stats?.target_fps ?? 'n/a'} encode_ms=${after.stats?.average_encode_ms ?? 'n/a'} frame_bytes=${after.stats?.last_frame_bytes ?? 'n/a'}`);
    lines.push('------------------------------------------------------------------------');
    lines.push(JSON.stringify({ before, after }, null, 2));
    if (fpsPanel) fpsPanel.textContent = lines.join('\n');
  } catch (error) {
    setFpsCode('PISD-TEST-017');
    if (fpsPanel) fpsPanel.textContent = `FAIL PISD-TEST-017 fps.max_test - ${String(error)}`;
  }
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
  await step('api.camera.fps_stats', 'GET', '/api/camera/fps-stats', undefined, (_r, payload) => payload.code === 'PISD-OK-000' && payload.stats);
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
  if (call.path.includes('/camera/start')) {
    startLivePreview();
  }
  if (call.path.includes('/camera/stop')) {
    refreshFrame();
  }
  if (call.path.includes('/camera/start') || call.path.includes('/camera/stop') || call.path.includes('/control/stop')) {
    await refreshStatus();
  }
});

document.getElementById('refreshStatusBtn').addEventListener('click', refreshStatus);
document.getElementById('refreshFrameBtn').addEventListener('click', refreshFrame);
document.getElementById('startLivePreviewBtn').addEventListener('click', startCameraAndLivePreview);
document.getElementById('applyFastPreviewBtn').addEventListener('click', applyFastPreviewPreset);
document.getElementById('readFpsStatsBtn').addEventListener('click', () => readFpsStats());
document.getElementById('runMaxFpsBtn').addEventListener('click', runMaxFpsTest);
document.getElementById('runSmokeTestBtn').addEventListener('click', runSafeSmokeTest);
document.getElementById('runSmokeTestBtn2').addEventListener('click', runSafeSmokeTest);
document.getElementById('stopAllBtn').addEventListener('click', async () => {
  await apiCall('POST', '/api/control/stop', {});
  await refreshStatus();
});
document.getElementById('applyCameraBtn').addEventListener('click', async () => {
  const payload = formToJson(document.getElementById('cameraSettingsForm'));
  await apiCall('POST', '/api/camera/apply', payload);
  startLivePreview();
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
setInterval(refreshStatus, 3000);
