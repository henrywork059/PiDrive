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

function populateConfig(config) {
  const session = config.session || {};
  const drive = config.drive || {};
  document.getElementById('routeText').value = session.route_text || '';
  document.getElementById('targetClassId').value = session.target_class_id ?? 1;
  document.getElementById('confidenceThreshold').value = session.confidence_threshold ?? 0.25;
  document.getElementById('iouThreshold').value = session.iou_threshold ?? 0.45;
  document.getElementById('loopTick').value = session.loop_tick_s ?? 0.08;
  document.getElementById('alignKp').value = drive.align_kp ?? 1.0;
  document.getElementById('maxSteering').value = drive.max_steering ?? 0.85;
  document.getElementById('centerTolerance').value = drive.center_tolerance_ratio ?? 0.1;
  document.getElementById('approachSpeed').value = drive.approach_speed ?? 0.2;
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
      align_kp: Number(document.getElementById('alignKp').value || 1.0),
      max_steering: Number(document.getElementById('maxSteering').value || 0.85),
      center_tolerance_ratio: Number(document.getElementById('centerTolerance').value || 0.1),
      approach_speed: Number(document.getElementById('approachSpeed').value || 0.2),
    },
  };
}

function renderModelList(status) {
  const select = document.getElementById('modelSelect');
  const models = status.models || [];
  const active = status.active_model || 'none';
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
    option.selected = model === active;
    select.appendChild(option);
  }
}

function renderStatus(status) {
  const statusEl = document.getElementById('status');
  const camera = status.camera || {};
  const motor = status.motor_config || {};
  statusEl.innerHTML = `
    <div class="status-grid">
      <div class="status-label">Running</div><div>${escapeHtml(status.running)}</div>
      <div class="status-label">Phase</div><div>${escapeHtml(status.phase)}</div>
      <div class="status-label">Detail</div><div>${escapeHtml(status.detail)}</div>
      <div class="status-label">Active model</div><div>${escapeHtml(status.active_model || 'none')}</div>
      <div class="status-label">AI backend</div><div>${escapeHtml(status.ai_ready)} | ${escapeHtml(status.ai_message || '')}</div>
      <div class="status-label">Target found</div><div>${escapeHtml(status.target_found)}</div>
      <div class="status-label">Current leg</div><div>${escapeHtml(status.active_leg_name || '-')}</div>
      <div class="status-label">Command</div><div>steer=${fmt(status.last_command?.steering)} throttle=${fmt(status.last_command?.throttle)} note=${escapeHtml(status.last_command?.note || '')}</div>
      <div class="status-label">Camera</div><div>${escapeHtml(camera.backend || 'offline')} | live=${escapeHtml(camera.preview_live ?? false)} | fps=${fmt(camera.fps || 0, 1)}</div>
      <div class="status-label">Motor GPIO</div><div>${escapeHtml(motor.gpio_available ?? false)}</div>
      <div class="status-label">Last error</div><div>${escapeHtml(status.last_error || camera.error || '-')}</div>
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
  renderViewer(status);
}

function renderViewer(status) {
  const overlay = document.getElementById('frameOverlay');
  const video = document.getElementById('videoFeed');
  const note = document.getElementById('viewerNote');
  const frame = status.frame || { width: 640, height: 360 };
  overlay.setAttribute('viewBox', `0 0 ${frame.width || 640} ${frame.height || 360}`);
  overlay.innerHTML = '';

  if ((status.camera || {}).running) {
    video.style.display = 'block';
    video.src = `/api/frame.jpg?t=${Date.now()}`;
    note.textContent = 'Camera is active after the start route. Green boxes are detections. Yellow is the current target class.';
  } else {
    video.style.display = 'none';
    note.textContent = 'Camera is still off until the start route finishes.';
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', String(frame.width || 640));
    bg.setAttribute('height', String(frame.height || 360));
    bg.setAttribute('fill', '#030712');
    overlay.appendChild(bg);
  }

  const targetId = String(document.getElementById('targetClassId').value || '1');
  for (const det of status.detections || []) {
    const b = det.box || {};
    const isTarget = String(det.label) === targetId;
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', b.x1 || 0);
    rect.setAttribute('y', b.y1 || 0);
    rect.setAttribute('width', Math.max(0, (b.x2 || 0) - (b.x1 || 0)));
    rect.setAttribute('height', Math.max(0, (b.y2 || 0) - (b.y1 || 0)));
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', isTarget ? '#facc15' : '#22c55e');
    rect.setAttribute('stroke-width', isTarget ? '3' : '2');
    overlay.appendChild(rect);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', b.x1 || 0);
    text.setAttribute('y', Math.max(14, (b.y1 || 0) - 4));
    text.setAttribute('fill', isTarget ? '#fde68a' : '#86efac');
    text.setAttribute('font-size', '12');
    text.textContent = `${det.label} ${(Number(det.confidence || 0) * 100).toFixed(0)}%`;
    overlay.appendChild(text);
  }
}

async function saveConfig() {
  try {
    const data = await postJSON('/api/config', collectConfig());
    populateConfig(data.config || {});
    setMessage('configMessage', data.message || 'Mission 1 config saved.');
    await refresh();
  } catch (err) {
    setMessage('configMessage', err.message || 'Failed to save config.', true);
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
    setMessage('modelMessage', data.message || 'Model uploaded and loaded.');
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
    setMessage('modelMessage', data.message || 'Model loaded.');
    await refresh();
  } catch (err) {
    setMessage('modelMessage', err.message || 'Failed to load model.', true);
  }
}

async function refresh() {
  try {
    const status = await fetchJSON('/api/status');
    renderStatus(status);
  } catch (err) {
    setMessage('configMessage', err.message || 'Refresh failed.', true);
  }
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
  setInterval(refresh, 500);
}

document.getElementById('saveConfigBtn').onclick = saveConfig;
document.getElementById('startBtn').onclick = startMission;
document.getElementById('stopBtn').onclick = stopMission;
document.getElementById('uploadModelBtn').onclick = uploadModel;
document.getElementById('loadModelBtn').onclick = loadSelectedModel;

init();
