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
  document.getElementById('forwardSpeed').value = drive.forward_speed ?? drive.approach_speed ?? 0.22;
  document.getElementById('turnK').value = drive.turn_k ?? 0.005;
  document.getElementById('turnSpeedMax').value = drive.turn_speed_max ?? drive.max_steering ?? 0.75;
  document.getElementById('deadbandRatio').value = drive.target_x_deadband_ratio ?? 0.05;
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

function renderStatus(status) {
  const statusEl = document.getElementById('status');
  const camera = status.camera || {};
  const motor = status.motor_config || {};
  const pipeline = status.pipeline || {};
  const target = status.target_detection || {};
  const targetCenter = target.center || {};
  const targetBox = target.box || {};
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
      <div class="status-label">Target found</div><div>${escapeHtml(status.target_found)}</div>
      <div class="status-label">Target side</div><div>${escapeHtml(status.target_side || '-')}</div>
      <div class="status-label">Car turn</div><div>${escapeHtml(status.car_turn_direction || '-')}</div>
      <div class="status-label">Target center</div><div>x=${fmt(targetCenter.x, 1)} y=${fmt(targetCenter.y, 1)}</div>
      <div class="status-label">Target box</div><div>w=${fmt(targetBox.width, 1)} h=${fmt(targetBox.height, 1)}</div>
      <div class="status-label">Command</div><div>left=${fmt(status.last_command?.left, 2)} right=${fmt(status.last_command?.right, 2)} note=${escapeHtml(status.last_command?.note || '')}</div>
      <div class="status-label">Motor GPIO</div><div>${escapeHtml(motor.gpio_available ?? false)}</div>
      <div class="status-label">Output summary</div><div>${escapeHtml(status.last_output_summary || '-')}</div>
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
  renderDetections(status);
  renderViewer(status);
}

function renderViewer(status) {
  const video = document.getElementById('videoFeed');
  const note = document.getElementById('viewerNote');
  if ((status.camera || {}).running && (status.phase || '').startsWith('ai')) {
    video.style.display = 'block';
    video.src = `/api/frame.jpg?t=${Date.now()}`;
    note.textContent = `Pi-generated annotated frame. Target side: ${status.target_side || 'none'}. Car turn: ${status.car_turn_direction || 'stopped'}. FPS: ${fmt(status.pipeline?.fps || 0, 2)}.`;
  } else if ((status.phase || '') === 'start_route' || (status.phase || '') === 'route_pending') {
    video.style.display = 'none';
    note.textContent = 'Camera is still off while the start route is running.';
  } else {
    video.style.display = 'none';
    note.textContent = 'Annotated frame will appear here after the route, camera start, and model load steps complete.';
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
  setInterval(refresh, 400);
}

document.getElementById('saveConfigBtn').onclick = saveConfig;
document.getElementById('startBtn').onclick = startMission;
document.getElementById('stopBtn').onclick = stopMission;
document.getElementById('uploadModelBtn').onclick = uploadModel;
document.getElementById('loadModelBtn').onclick = loadSelectedModel;

init();
