async function postJSON(path, body = {}) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

function num(id, fallback = 0) {
  const v = Number(document.getElementById(id).value);
  return Number.isFinite(v) ? v : fallback;
}

function setIf(id, value) {
  const el = document.getElementById(id);
  if (el && value !== undefined && value !== null) el.value = value;
}

function renderStatus(status) {
  document.getElementById('modeSel').value = status.mode;
  const s = document.getElementById('status');
  s.innerHTML = `
    <div><b>Mode:</b> ${status.mode}</div>
    <div><b>Running:</b> ${status.running}</div>
    <div><b>State:</b> ${status.state}</div>
    <div><b>Detail:</b> ${status.detail}</div>
    <div><b>Retries:</b> ${status.retries}</div>
    <div><b>Completed cycles:</b> ${status.completed_cycles}/${status.max_cycles}</div>
    <div><b>Active leg:</b> ${status.active_route_leg || '-'}</div>
    <div><b>Detections:</b> ${(status.detections || []).length}</div>
    <div><b>Cmd:</b> steer=${status.last_command.steering.toFixed(2)}, throttle=${status.last_command.throttle.toFixed(2)}</div>
  `;

  const logs = document.getElementById('logs');
  logs.textContent = (status.logs || []).map((entry) =>
    `[${entry.timestamp.toFixed(2)}] ${entry.action}: ${entry.detail}`
  ).join('\n');

  const cfg = status.settings || {};
  const cam = cfg.camera || {};
  const mot = cfg.motor || {};
  const rt = cfg.runtime || {};
  setIf('cam_width', cam.width);
  setIf('cam_height', cam.height);
  setIf('cam_fps', cam.fps);
  setIf('cam_preview_fps', cam.preview_fps);
  setIf('cam_preview_quality', cam.preview_quality);
  setIf('mot_left_max_speed', mot.left_max_speed);
  setIf('mot_right_max_speed', mot.right_max_speed);
  setIf('mot_left_bias', mot.left_bias);
  setIf('mot_right_bias', mot.right_bias);
  setIf('rt_steer_mix', rt.steer_mix);
}

async function refresh() {
  const res = await fetch('/api/status');
  const status = await res.json();
  renderStatus(status);
}

document.getElementById('startBtn').onclick = async () => { await postJSON('/api/start', { tick_s: 0.1 }); await refresh(); };
document.getElementById('stopBtn').onclick = async () => { await postJSON('/api/stop'); await refresh(); };
document.getElementById('stepBtn').onclick = async () => { await postJSON('/api/step'); await refresh(); };

document.getElementById('resetBtn').onclick = async () => {
  const max_cycles = Number(document.getElementById('maxCycles').value || 2);
  const mode = document.getElementById('modeSel').value;
  await postJSON('/api/reset', { max_cycles, mode });
  document.getElementById('videoFeed').src = `/video_feed?ts=${Date.now()}`;
  await refresh();
};

document.getElementById('saveSettingsBtn').onclick = async () => {
  const settings = {
    camera: {
      width: num('cam_width', 426),
      height: num('cam_height', 240),
      fps: num('cam_fps', 30),
      preview_fps: num('cam_preview_fps', 12),
      preview_quality: num('cam_preview_quality', 60),
    },
    motor: {
      left_max_speed: num('mot_left_max_speed', 1.0),
      right_max_speed: num('mot_right_max_speed', 1.0),
      left_bias: num('mot_left_bias', 0.0),
      right_bias: num('mot_right_bias', 0.0),
    },
    runtime: { steer_mix: num('rt_steer_mix', 0.75) },
  };
  await postJSON('/api/settings/save', { settings });
  await refresh();
};

setInterval(refresh, 500);
refresh();
