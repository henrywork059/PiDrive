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

let runSettingsLoaded = false;

function renderStatus(status) {
  const s = document.getElementById('status');
  const camera = status.camera || {};
  const runSettings = status.run_settings || {};
  s.innerHTML = `
    <div><b>Launch mode:</b> GUI</div>
    <div><b>Runtime backend:</b> ${status.mode} (requested: ${status.mode_requested || status.mode})</div>
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
    <div><b>Saved run defaults:</b> backend=${runSettings.runtime_mode || '-'} | cycles=${runSettings.max_cycles ?? '-'} | headless_tick=${fmt(runSettings.headless_tick_s || 0.2)} | gui_tick=${fmt(runSettings.gui_tick_s || 0.2)}</div>
    ${status.fallback_reason ? `<div><b>Mode note:</b> ${status.fallback_reason}</div>` : ''}
    ${camera.error ? `<div><b>Camera error:</b> ${camera.error}</div>` : ''}
  `;

  const logs = document.getElementById('logs');
  logs.textContent = (status.logs || []).map((entry) =>
    `[${fmt(entry.timestamp, 2)}] ${entry.action}: ${entry.detail}`
  ).join('\n');

  renderViewer(status);

  if (!runSettingsLoaded && status.run_settings) {
    populateRunSettingsForm(status.run_settings);
    runSettingsLoaded = true;
  }
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

function populateRunSettingsForm(settings) {
  document.getElementById('savedRuntimeMode').value = settings.runtime_mode || 'sim';
  document.getElementById('savedMaxCycles').value = settings.max_cycles ?? 2;
  document.getElementById('savedHeadlessTick').value = settings.headless_tick_s ?? 0.2;
  document.getElementById('savedGuiTick').value = settings.gui_tick_s ?? 0.2;
  document.getElementById('savedAutoStartGui').checked = Boolean(settings.auto_start_gui);

  document.getElementById('maxCycles').value = settings.max_cycles ?? 2;
  document.getElementById('tickSeconds').value = settings.gui_tick_s ?? 0.2;
}

function collectRunSettingsForm() {
  return {
    runtime_mode: document.getElementById('savedRuntimeMode').value || 'sim',
    max_cycles: Number(document.getElementById('savedMaxCycles').value || 2),
    headless_tick_s: Number(document.getElementById('savedHeadlessTick').value || 0.2),
    gui_tick_s: Number(document.getElementById('savedGuiTick').value || 0.2),
    auto_start_gui: document.getElementById('savedAutoStartGui').checked,
  };
}

function setSaveMessage(message, isError = false) {
  const el = document.getElementById('saveMessage');
  el.textContent = message || '';
  el.classList.toggle('error', Boolean(isError));
}

async function loadRunSettings() {
  const res = await fetch('/api/run-settings');
  const data = await res.json();
  if (data.ok && data.run_settings) {
    populateRunSettingsForm(data.run_settings);
    runSettingsLoaded = true;
    setSaveMessage('Saved run settings reloaded.');
  }
}

async function saveRunSettings() {
  const payload = collectRunSettingsForm();
  const data = await postJSON('/api/run-settings', payload);
  if (data.ok) {
    if (data.run_settings) {
      populateRunSettingsForm(data.run_settings);
      runSettingsLoaded = true;
    }
    setSaveMessage(data.message || 'Run settings saved.');
    await refresh();
  } else {
    setSaveMessage(data.message || 'Failed to save run settings.', true);
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
document.getElementById('saveRunSettingsBtn').onclick = saveRunSettings;
document.getElementById('reloadRunSettingsBtn').onclick = loadRunSettings;

setInterval(refresh, 500);
loadRunSettings().then(refresh);
