async function postJSON(path, body = {}) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

function fmt(n, digits = 2) {
  const value = Number(n);
  return Number.isFinite(value) ? value.toFixed(digits) : '0.00';
}

function renderStatus(status) {
  const s = document.getElementById('status');
  const camera = status.camera || {};
  s.innerHTML = `
    <div><b>Mode:</b> ${status.mode} (requested: ${status.mode_requested || status.mode})</div>
    <div><b>Running:</b> ${status.running}</div>
    <div><b>State:</b> ${status.state}</div>
    <div><b>Detail:</b> ${status.detail}</div>
    <div><b>Retries:</b> ${status.retries}</div>
    <div><b>Completed cycles:</b> ${status.completed_cycles}/${status.max_cycles}</div>
    <div><b>Active leg:</b> ${status.active_route_leg || '-'}</div>
    <div><b>Cmd:</b> steer=${fmt(status.last_command.steering)}, throttle=${fmt(status.last_command.throttle)}, note=${status.last_command.note}</div>
    <div><b>Camera:</b> ${camera.backend || '-'} | live=${camera.preview_live ?? false} | fps=${fmt(camera.fps || 0, 1)}</div>
    <div><b>Perception:</b> ${status.perception_ready ?? true} ${status.perception_message ? `| ${status.perception_message}` : ''}</div>
    <div><b>Arm bound:</b> ${status.arm_bound ?? false} | <b>Virtual grab:</b> ${status.virtual_grab ?? false}</div>
    ${status.fallback_reason ? `<div><b>Mode note:</b> ${status.fallback_reason}</div>` : ''}
    ${camera.error ? `<div><b>Camera error:</b> ${camera.error}</div>` : ''}
  `;

  const logs = document.getElementById('logs');
  logs.textContent = (status.logs || []).map((entry) =>
    `[${fmt(entry.timestamp, 2)}] ${entry.action}: ${entry.detail}`
  ).join('\n');

  renderViewer(status);
}

function renderViewer(status) {
  const overlay = document.getElementById('frameOverlay');
  const video = document.getElementById('videoFeed');
  const note = document.getElementById('viewerNote');
  const frame = status.frame || { width: 640, height: 360 };
  overlay.setAttribute('viewBox', `0 0 ${frame.width || 640} ${frame.height || 360}`);
  overlay.innerHTML = '';

  if (status.mode === 'live' && (status.camera || {}).preview_live) {
    video.style.display = 'block';
    video.src = `/api/frame.jpg?t=${Date.now()}`;
    note.textContent = 'Live camera feed with detection overlay.';
  } else {
    video.style.display = 'none';
    note.textContent = status.mode === 'live'
      ? 'Live mode is active but the camera preview is not available yet.'
      : 'Simulation mode draws detections on a blank reference canvas.';
    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('x', '0');
    bg.setAttribute('y', '0');
    bg.setAttribute('width', String(frame.width || 640));
    bg.setAttribute('height', String(frame.height || 360));
    bg.setAttribute('fill', '#0b1220');
    overlay.appendChild(bg);
  }

  for (const det of status.detections || []) {
    const b = det.box;
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', b.x1);
    rect.setAttribute('y', b.y1);
    rect.setAttribute('width', b.x2 - b.x1);
    rect.setAttribute('height', b.y2 - b.y1);
    rect.setAttribute('fill', 'none');
    rect.setAttribute('stroke', det.label === 'he3_zone' ? '#38bdf8' : '#22c55e');
    rect.setAttribute('stroke-width', '2');
    overlay.appendChild(rect);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', b.x1);
    text.setAttribute('y', Math.max(14, b.y1 - 4));
    text.setAttribute('fill', det.label === 'he3_zone' ? '#7dd3fc' : '#86efac');
    text.setAttribute('font-size', '12');
    text.textContent = `${det.label} ${(det.confidence * 100).toFixed(0)}%`;
    overlay.appendChild(text);
  }
}

async function refresh() {
  const res = await fetch('/api/status');
  const status = await res.json();
  renderStatus(status);
}

document.getElementById('startBtn').onclick = async () => {
  const tick_s = Number(document.getElementById('tickSeconds').value || 0.2);
  await postJSON('/api/start', { tick_s });
  await refresh();
};
document.getElementById('stopBtn').onclick = async () => {
  await postJSON('/api/stop');
  await refresh();
};
document.getElementById('stepBtn').onclick = async () => {
  await postJSON('/api/step');
  await refresh();
};
document.getElementById('resetBtn').onclick = async () => {
  const max_cycles = Number(document.getElementById('maxCycles').value || 2);
  await postJSON('/api/reset', { max_cycles });
  await refresh();
};

setInterval(refresh, 500);
refresh();
