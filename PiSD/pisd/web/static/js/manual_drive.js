(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const initialStatus = JSON.parse($('manualDriveInitialStatus')?.textContent || '{}');
  const LEGACY_STORAGE_KEY = 'pisd.manualDrive.v1';
  const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v2';
  const DEFAULTS = { speed: 0.18, max_speed_limit: 0.65, steer_strength: 0.35, drag_send_interval_ms: 90, recording_fps: 6 };
  const globalCode = $('mdrvGlobalCode');
  const preview = $('mdrvPreview');
  const log = $('mdrvLog');
  const logPanel = $('manualDriveLogPanel');
  const toggleLog = $('mdrvToggleLog');
  const arm = $('mdrvArm');
  const speed = $('mdrvSpeed');
  const steer = $('mdrvSteer');
  const speedOut = $('mdrvSpeedOut');
  const steerOut = $('mdrvSteerOut');
  const throttleOut = $('mdrvThrottleOut');
  const steeringOut = $('mdrvSteeringOut');
  const safetyText = $('mdrvSafetyText');
  const pad = $('mdrvDragPad');
  const knob = $('mdrvDragKnob');
  const recordButton = $('mdrvRecordToggle');
  let dragging = false;
  let lastSentAt = 0;
  let lastPayload = { steering: 0, throttle: 0, steer_mix: 1.0 };
  let recordingRunning = Boolean(initialStatus.recording?.running);

  function isOk(code) { return String(code || '').startsWith('PISD-OK'); }
  function clamp(value, min, max, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
  }
  function maxSpeedLimit() {
    return clamp(readRuntimeLocal().manual_drive?.max_speed_limit || DEFAULTS.max_speed_limit, 0.1, 0.65, DEFAULTS.max_speed_limit);
  }
  function setCode(target, code) {
    const value = code || 'PISD-OK-000';
    const element = typeof target === 'string' ? document.querySelector(`[data-code-for="${target}"]`) : target;
    if (!element) return;
    element.textContent = value;
    element.dataset.state = isOk(value) ? 'ok' : 'error';
  }
  function setGlobalCode(code) { setCode(globalCode, code); }

  function readRuntimeLocal() {
    try { return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}') || {}; }
    catch (_err) { return {}; }
  }

  function writeRuntimeLocal(partial) {
    const current = readRuntimeLocal();
    const next = { ...current, ...partial, saved_at: new Date().toISOString() };
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next));
    return next;
  }

  function readLegacyPrefs() {
    try { return JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY) || '{}') || {}; }
    catch (_err) { return {}; }
  }

  async function loadSettings() {
    let settings = readRuntimeLocal();
    try {
      const response = await fetch('/api/settings', { cache: 'no-store' });
      if (response.ok) {
        const payload = await response.json();
        if (payload.settings) {
          settings = payload.settings;
          localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
        }
      }
    } catch (_err) {}
    const legacy = readLegacyPrefs();
    const serverManual = settings.manual_drive || {};
    const limit = clamp(serverManual.max_speed_limit || DEFAULTS.max_speed_limit, 0.1, 0.65, DEFAULTS.max_speed_limit);
    const manual = {
      ...DEFAULTS,
      ...serverManual,
      max_speed_limit: limit,
      speed: clamp(legacy.speed || serverManual.speed || DEFAULTS.speed, 0.0, limit, DEFAULTS.speed),
      steer_strength: clamp(legacy.steer || serverManual.steer_strength || DEFAULTS.steer_strength, 0.0, 1.0, DEFAULTS.steer_strength),
    };
    if (speed) { speed.max = String(manual.max_speed_limit); speed.value = manual.speed; }
    if (steer) steer.value = manual.steer_strength;
    updateSliderLabels();
    if (window.PiSDPanelPresentation && settings.panel_presentation) window.PiSDPanelPresentation.apply(settings.panel_presentation);
  }

  async function persistManualSettings() {
    const limit = maxSpeedLimit();
    const manual_drive = {
      speed: clamp(speed?.value || DEFAULTS.speed, 0, limit, DEFAULTS.speed),
      max_speed_limit: limit,
      steer_strength: clamp(steer?.value || DEFAULTS.steer_strength, 0, 1, DEFAULTS.steer_strength),
      drag_send_interval_ms: DEFAULTS.drag_send_interval_ms,
      recording_fps: clamp(readRuntimeLocal().manual_drive?.recording_fps || DEFAULTS.recording_fps, 0.2, 30, DEFAULTS.recording_fps),
    };
    writeRuntimeLocal({ manual_drive });
    localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify({ speed: String(manual_drive.speed), steer: String(manual_drive.steer_strength) }));
    try {
      await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ manual_drive }) });
    } catch (_err) {}
  }

  function writeLog(action, payload, httpStatus = '') {
    const code = payload?.code || (httpStatus >= 400 ? 'PISD-API-002' : 'PISD-OK-000');
    setGlobalCode(code);
    setCode('log', code);
    if (log) log.textContent = JSON.stringify({ action, http_status: httpStatus, response: payload }, null, 2);
    const short = $('mdrvShortStatus');
    if (short) short.textContent = `${action}: ${code} ${payload?.message || ''}`.trim();
  }

  async function api(method, path, body, codeTarget = 'log') {
    const options = { method, headers: {} };
    if (body !== undefined && method !== 'GET') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json') ? await response.json() : { ok: response.ok, code: response.ok ? 'PISD-OK-000' : 'PISD-API-002', message: await response.text() };
    setCode(codeTarget, payload.code);
    writeLog(`${method} ${path}`, payload, response.status);
    return { response, payload };
  }

  function renderStatus(status) {
    $('mdrvHardware').textContent = status.hardware_requested ? 'on' : 'sim';
    $('mdrvCameraState').textContent = status.camera?.running ? 'run' : (status.camera?.backend || 'off');
    $('mdrvMotorState').textContent = status.motor?.hardware_enabled ? 'hw' : 'sim';
    $('mdrvCameraFps').textContent = status.camera?.measured_capture_fps ?? status.camera?.fps ?? 'n/a';
    const rec = Boolean(status.recording?.running);
    recordingRunning = rec;
    const recState = $('mdrvRecordingState');
    if (recState) recState.textContent = rec ? 'on' : 'off';
    if (recordButton) {
      recordButton.textContent = rec ? 'Stop record' : 'Record';
      recordButton.classList.toggle('mdrv-recording-on', rec);
    }
    setCode('status', status.code || 'PISD-OK-000');
    setGlobalCode(status.code || 'PISD-OK-000');
  }

  async function refreshStatus() {
    try {
      const { payload } = await api('GET', '/api/status', undefined, 'status');
      renderStatus(payload);
    } catch (err) {
      writeLog('refresh status failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function updateSliderLabels() {
    const limit = maxSpeedLimit();
    if (speed) { speed.max = String(limit); if (Number(speed.value) > limit) speed.value = String(limit); }
    if (speedOut) speedOut.textContent = currentSpeed().toFixed(2);
    if (steerOut) steerOut.textContent = currentSteer().toFixed(2);
  }

  function currentSpeed() { return clamp(speed?.value || DEFAULTS.speed, 0, maxSpeedLimit(), DEFAULTS.speed); }
  function currentSteer() { return clamp(steer?.value || DEFAULTS.steer_strength, 0, 1, DEFAULTS.steer_strength); }

  function updateLock() {
    const enabled = Boolean(arm?.checked);
    pad?.classList.toggle('is-locked', !enabled);
    if (safetyText) safetyText.textContent = enabled
      ? 'Drag within the pad to drive. Release to stop. Keep the wheels lifted until calibration is complete.'
      : 'Drag pad is locked until motor output is enabled. STOP is always active.';
  }

  function setKnob(normX, normY) {
    const clampedX = clamp(normX, -1, 1, 0);
    const clampedY = clamp(normY, -1, 1, 0);
    knob?.style.setProperty('--knob-left', `${(clampedX + 1) * 50}%`);
    knob?.style.setProperty('--knob-top', `${(clampedY + 1) * 50}%`);
    if (steeringOut) steeringOut.textContent = (clampedX * currentSteer()).toFixed(2);
    if (throttleOut) throttleOut.textContent = (-clampedY * currentSpeed()).toFixed(2);
    return { x: clampedX, y: clampedY };
  }

  function payloadFromPointer(event) {
    const rect = pad.getBoundingClientRect();
    const safeWidth = Math.max(1, rect.width);
    const safeHeight = Math.max(1, rect.height);
    const x = ((event.clientX - rect.left) / safeWidth - 0.5) * 2;
    const y = ((event.clientY - rect.top) / safeHeight - 0.5) * 2;
    const norm = setKnob(x, y);
    return {
      steering: clamp(norm.x * currentSteer(), -1, 1, 0),
      throttle: clamp(-norm.y * currentSpeed(), -1, 1, 0),
      steer_mix: 1.0,
    };
  }

  async function sendManual(payload, force = false) {
    if (!arm?.checked) {
      const blocked = { ok: false, code: 'PISD-MOT-008', message: 'Manual drag pad is locked on the page. Enable motor output first.' };
      setCode('drive', blocked.code);
      writeLog('manual drag blocked', blocked, 0);
      return;
    }
    const now = performance.now();
    const interval = Number(readRuntimeLocal().manual_drive?.drag_send_interval_ms || DEFAULTS.drag_send_interval_ms);
    if (!force && now - lastSentAt < interval) return;
    lastSentAt = now;
    lastPayload = payload;
    try { await api('POST', '/api/control/manual', payload, 'drive'); }
    catch (err) { writeLog('manual drag failed', { ok: false, code: 'PISD-API-002', message: String(err) }); }
  }

  async function stopAll(target = 'stop') {
    setKnob(0, 0);
    try {
      await api('POST', '/api/control/stop', {}, target);
      await refreshStatus();
    } catch (err) {
      writeLog('STOP failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function livePreview() { if (preview) preview.src = `/video_feed?t=${Date.now()}`; }
  function snapshotView() { if (preview) preview.src = `/api/camera/frame.jpg?t=${Date.now()}`; }

  async function captureFrame() {
    try {
      await api('POST', '/api/recording/capture', { label: 'manual_capture' }, 'camera');
      await refreshStatus();
    } catch (err) {
      writeLog('capture frame failed', { ok: false, code: 'PISD-REC-002', message: String(err) });
    }
  }

  async function toggleRecording() {
    const manual = readRuntimeLocal().manual_drive || {};
    try {
      if (recordingRunning) {
        await api('POST', '/api/recording/stop', {}, 'camera');
      } else {
        await api('POST', '/api/recording/start', { label: 'manual_drive', fps: manual.recording_fps || DEFAULTS.recording_fps }, 'camera');
      }
      await refreshStatus();
    } catch (err) {
      writeLog('toggle recording failed', { ok: false, code: 'PISD-REC-002', message: String(err) });
    }
  }

  function bindPad() {
    if (!pad) return;
    pad.addEventListener('pointerdown', event => {
      if (!arm?.checked) { updateLock(); writeLog('manual drag blocked', { ok: false, code: 'PISD-MOT-008', message: 'Enable motor output first.' }, 0); return; }
      event.preventDefault();
      dragging = true;
      pad.setPointerCapture(event.pointerId);
      sendManual(payloadFromPointer(event), true);
    });
    pad.addEventListener('pointermove', event => { if (dragging) { event.preventDefault(); sendManual(payloadFromPointer(event)); } });
    function release(event) {
      if (!dragging) return;
      dragging = false;
      try { pad.releasePointerCapture(event.pointerId); } catch (_err) {}
      stopAll('drive');
    }
    pad.addEventListener('pointerup', release);
    pad.addEventListener('pointercancel', release);
    pad.addEventListener('mouseleave', () => { if (dragging) stopAll('drive'); dragging = false; });
  }

  function bind() {
    $('mdrvRefresh')?.addEventListener('click', refreshStatus);
    $('mdrvStartCamera')?.addEventListener('click', async () => { await api('POST', '/api/camera/start', {}, 'camera'); livePreview(); await refreshStatus(); });
    $('mdrvLiveCamera')?.addEventListener('click', livePreview);
    $('mdrvSnapshot')?.addEventListener('click', snapshotView);
    $('mdrvCaptureFrame')?.addEventListener('click', captureFrame);
    recordButton?.addEventListener('click', toggleRecording);
    $('mdrvStopTop')?.addEventListener('click', () => stopAll('stop'));
    $('mdrvStopPad')?.addEventListener('click', () => stopAll('drive'));
    $('mdrvStopBig')?.addEventListener('click', () => stopAll('stop'));
    toggleLog?.addEventListener('click', () => {
      const hidden = logPanel?.hasAttribute('hidden');
      if (hidden) logPanel.removeAttribute('hidden'); else logPanel?.setAttribute('hidden', '');
      toggleLog.textContent = hidden ? 'Hide action log' : 'Show action log';
    });
    arm?.addEventListener('change', updateLock);
    speed?.addEventListener('input', () => { updateSliderLabels(); persistManualSettings(); setKnob(lastPayload.steering / Math.max(0.001, currentSteer()), -lastPayload.throttle / Math.max(0.001, currentSpeed())); });
    steer?.addEventListener('input', () => { updateSliderLabels(); persistManualSettings(); setKnob(lastPayload.steering / Math.max(0.001, currentSteer()), -lastPayload.throttle / Math.max(0.001, currentSpeed())); });
    bindPad();
  }

  setKnob(0, 0);
  renderStatus(initialStatus);
  bind();
  updateLock();
  loadSettings();
})();
