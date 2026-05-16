(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const initialStatus = JSON.parse($('manualDriveInitialStatus')?.textContent || '{}');
  const STORAGE_KEY = 'pisd.manualDrive.v1';
  const DEFAULTS = { speed: '0.18', steer: '0.35' };
  const globalCode = $('mdrvGlobalCode');
  const preview = $('mdrvPreview');
  const statusText = $('mdrvStatusText');
  const log = $('mdrvLog');
  const arm = $('mdrvArm');
  const speed = $('mdrvSpeed');
  const steer = $('mdrvSteer');
  const speedOut = $('mdrvSpeedOut');
  const steerOut = $('mdrvSteerOut');
  const safetyText = $('mdrvSafetyText');
  const driveButtons = Array.from(document.querySelectorAll('.mdrv-drive[data-steering]'));

  function readManualPrefs() {
    try { return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {}) }; }
    catch (_err) { return { ...DEFAULTS }; }
  }

  function saveManualPrefs() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ speed: speed.value, steer: steer.value }));
  }

  function isOk(code) { return String(code || '').startsWith('PISD-OK'); }
  function setCode(target, code) {
    const value = code || 'PISD-OK-000';
    const element = typeof target === 'string' ? document.querySelector(`[data-code-for="${target}"]`) : target;
    if (!element) return;
    element.textContent = value;
    element.dataset.state = isOk(value) ? 'ok' : 'error';
  }

  function setGlobalCode(code) { setCode(globalCode, code); }

  function writeLog(action, payload, httpStatus = '') {
    const code = payload?.code || (httpStatus >= 400 ? 'PISD-API-002' : 'PISD-OK-000');
    setGlobalCode(code);
    setCode('log', code);
    if (log) log.textContent = JSON.stringify({ action, http_status: httpStatus, response: payload }, null, 2);
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
    $('mdrvHardware').textContent = status.hardware_requested ? 'enabled' : 'simulation';
    $('mdrvCameraState').textContent = `${status.camera?.backend || 'unknown'} / ${status.camera?.running ? 'running' : 'stopped'}`;
    $('mdrvMotorState').textContent = `${status.motor?.adapter || 'unknown'} / ${status.motor?.hardware_enabled ? 'hardware' : 'simulation'}`;
    $('mdrvCameraFps').textContent = status.camera?.measured_capture_fps ?? status.camera?.fps ?? 'n/a';
    if (statusText) statusText.textContent = JSON.stringify(status, null, 2);
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

  function updateLock() {
    const enabled = Boolean(arm?.checked);
    driveButtons.forEach(button => { button.disabled = !enabled; });
    if (safetyText) safetyText.textContent = enabled
      ? 'Motor output enabled for this page. Keep the wheels lifted and use STOP before changing setup.'
      : 'Drive buttons are locked until motor output is enabled. STOP is always active.';
  }

  function currentSpeed() { return Number(speed?.value || DEFAULTS.speed); }
  function currentSteer() { return Number(steer?.value || DEFAULTS.steer); }

  function buttonPayload(button) {
    const throttleScale = Number(button.dataset.throttle || 0);
    const steeringScale = Number(button.dataset.steering || 0);
    return {
      throttle: throttleScale === 0 ? 0 : Math.sign(throttleScale) * currentSpeed() * Math.abs(throttleScale),
      steering: steeringScale === 0 ? 0 : Math.sign(steeringScale) * currentSteer() * Math.abs(steeringScale),
      steer_mix: 1.0,
    };
  }

  async function sendManual(button) {
    if (!arm?.checked) {
      const payload = { ok: false, code: 'PISD-MOT-008', message: 'Manual drive is locked on the page. Enable motor output first.' };
      setCode('drive', payload.code);
      writeLog('manual drive blocked', payload, 0);
      return;
    }
    try {
      await api('POST', '/api/control/manual', buttonPayload(button), 'drive');
    } catch (err) {
      writeLog('manual drive failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  async function stopAll(target = 'stop') {
    try {
      await api('POST', '/api/control/stop', {}, target);
      await refreshStatus();
    } catch (err) {
      writeLog('STOP failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function livePreview() { if (preview) preview.src = `/video_feed?t=${Date.now()}`; }
  function snapshot() { if (preview) preview.src = `/api/camera/frame.jpg?t=${Date.now()}`; }

  function loadPrefs() {
    const prefs = readManualPrefs();
    if (speed) speed.value = prefs.speed;
    if (steer) steer.value = prefs.steer;
    if (speedOut) speedOut.textContent = Number(speed.value).toFixed(2);
    if (steerOut) steerOut.textContent = Number(steer.value).toFixed(2);
  }

  function bind() {
    $('mdrvRefresh')?.addEventListener('click', refreshStatus);
    $('mdrvStartCamera')?.addEventListener('click', async () => { await api('POST', '/api/camera/start', {}, 'camera'); livePreview(); await refreshStatus(); });
    $('mdrvLiveCamera')?.addEventListener('click', livePreview);
    $('mdrvSnapshot')?.addEventListener('click', snapshot);
    $('mdrvStopTop')?.addEventListener('click', () => stopAll('stop'));
    $('mdrvStopPad')?.addEventListener('click', () => stopAll('drive'));
    $('mdrvStopBig')?.addEventListener('click', () => stopAll('stop'));
    arm?.addEventListener('change', updateLock);
    speed?.addEventListener('input', () => { speedOut.textContent = Number(speed.value).toFixed(2); saveManualPrefs(); });
    steer?.addEventListener('input', () => { steerOut.textContent = Number(steer.value).toFixed(2); saveManualPrefs(); });
    driveButtons.forEach(button => button.addEventListener('click', () => sendManual(button)));
  }

  loadPrefs();
  renderStatus(initialStatus);
  bind();
  updateLock();
})();
