(() => {
  const $ = (id) => document.getElementById(id);
  const initialStatus = JSON.parse($('autopilotInitialStatus')?.textContent || '{}');
  const IDLE_SRC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'%3E%3Crect width='1280' height='720' fill='%23020617'/%3E%3Ctext x='640' y='340' fill='%2394a3b8' font-family='Arial,sans-serif' font-size='42' text-anchor='middle'%3EAutopilot preview idle%3C/text%3E%3Ctext x='640' y='398' fill='%2364748b' font-family='Arial,sans-serif' font-size='26' text-anchor='middle'%3EStart camera or live stream when needed%3C/text%3E%3C/svg%3E";
  const els = {
    code: $('apGlobalCode'), runningPill: $('apRunningPill'), modePill: $('apModePill'), remainingPill: $('apRemainingPill'),
    safetyAck: $('apSafetyAck'), enableMotorOutput: $('apEnableMotorOutput'), mode: $('apMode'), throttle: $('apThrottle'), throttleOut: $('apThrottleOut'),
    steerLimit: $('apSteerLimit'), steerLimitOut: $('apSteerLimitOut'), steeringBias: $('apSteeringBias'), steeringBiasOut: $('apSteeringBiasOut'),
    duration: $('apDuration'), durationOut: $('apDurationOut'), tickHz: $('apTickHz'), tickHzOut: $('apTickHzOut'), notice: $('apControlNotice'), log: $('apLog'),
    previewFrame: $('apPreviewFrame'), previewImage: $('apPreviewImage'), path: $('apPath'), pathWide: $('apPathWide'), endpoint: $('apEndpoint'),
    dbgRunning: $('apDbgRunning'), dbgSource: $('apDbgSource'), dbgSteering: $('apDbgSteering'), dbgThrottle: $('apDbgThrottle'),
    dbgLeft: $('apDbgLeft'), dbgRight: $('apDbgRight'), dbgElapsed: $('apDbgElapsed'), dbgReason: $('apDbgReason'),
  };
  let statusTimer = 0;
  let lastRunning = false;

  function clamp(value, min, max, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
  }
  function signed(value) {
    const n = clamp(value, -1, 1, 0);
    return `${n >= 0 ? '+' : ''}${n.toFixed(2)}`;
  }
  function isOk(code) { return String(code || '').startsWith('PISD-OK'); }
  function setCode(target, code = 'PISD-OK-000') {
    const el = typeof target === 'string' ? document.querySelector(`[data-code-for="${target}"]`) : target;
    if (!el) return;
    el.textContent = code;
    el.dataset.state = isOk(code) ? 'ok' : 'error';
  }
  function setNotice(message, code = 'PISD-OK-000') {
    if (els.notice) {
      els.notice.textContent = message;
      els.notice.dataset.state = isOk(code) ? 'ok' : 'error';
    }
    if (els.code) els.code.textContent = code;
    setCode('control', code);
  }
  function writeLog(label, payload) {
    if (!els.log) return;
    const line = `[${new Date().toLocaleTimeString()}] ${label}\n${JSON.stringify(payload, null, 2)}\n`;
    els.log.textContent = `${line}\n${els.log.textContent || ''}`.slice(0, 9000);
  }
  async function api(method, path, body) {
    const options = { method, headers: {}, cache: 'no-store' };
    if (body !== undefined && method !== 'GET') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    const payload = await response.json();
    if (els.code && payload.code) els.code.textContent = payload.code;
    return { response, payload };
  }
  function readConfig() {
    return {
      mode: els.mode?.value || 'hold',
      max_throttle: clamp(els.throttle?.value, 0, 0.35, 0.16),
      steer_limit: clamp(els.steerLimit?.value, 0, 0.75, 0.35),
      steering_bias: clamp(els.steeringBias?.value, -0.35, 0.35, 0),
      max_run_seconds: clamp(els.duration?.value, 1, 60, 12),
      tick_hz: clamp(els.tickHz?.value, 2, 20, 8),
      steer_mix: 1.0,
      s_curve_period_s: 4.0,
    };
  }
  function applyConfigToControls(config = {}) {
    if (els.mode) els.mode.value = config.mode || 'hold';
    if (els.throttle) els.throttle.value = clamp(config.max_throttle, 0, 0.35, 0.16);
    if (els.steerLimit) els.steerLimit.value = clamp(config.steer_limit, 0, 0.75, 0.35);
    if (els.steeringBias) els.steeringBias.value = clamp(config.steering_bias, -0.35, 0.35, 0);
    if (els.duration) els.duration.value = clamp(config.max_run_seconds, 1, 60, 12);
    if (els.tickHz) els.tickHz.value = clamp(config.tick_hz, 2, 20, 8);
    updateLabels();
  }
  function updateLabels() {
    if (els.throttleOut) els.throttleOut.textContent = Number(els.throttle?.value || 0).toFixed(2);
    if (els.steerLimitOut) els.steerLimitOut.textContent = Number(els.steerLimit?.value || 0).toFixed(2);
    if (els.steeringBiasOut) els.steeringBiasOut.textContent = signed(els.steeringBias?.value || 0);
    if (els.durationOut) els.durationOut.textContent = `${Number(els.duration?.value || 0).toFixed(0)} s`;
    if (els.tickHzOut) els.tickHzOut.textContent = `${Number(els.tickHz?.value || 0).toFixed(0)} Hz`;
  }
  function pathFromCommand(throttle = 0, steering = 0) {
    const speed = Math.abs(clamp(throttle, -1, 1, 0));
    const reverse = throttle < -0.02;
    const length = 18 + speed * 52;
    const start = { x: 50, y: reverse ? 18 : 88 };
    const sign = reverse ? 1 : -1;
    const points = [];
    const curve = clamp(steering, -1, 1, 0) * (0.18 + speed * 0.55);
    for (let i = 0; i <= 24; i += 1) {
      const t = i / 24;
      const y = start.y + sign * length * t;
      const x = start.x + curve * 55 * t * t;
      points.push({ x: Math.max(8, Math.min(92, x)), y: Math.max(8, Math.min(92, y)) });
    }
    return points;
  }
  function renderPath(command = {}) {
    const throttle = clamp(command.throttle, -1, 1, 0);
    const steering = clamp(command.steering, -1, 1, 0);
    const points = pathFromCommand(throttle, steering);
    const d = points.map((p, idx) => `${idx ? 'L' : 'M'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ');
    if (els.path) els.path.setAttribute('d', d);
    if (els.pathWide) els.pathWide.setAttribute('d', d);
    const end = points[points.length - 1] || { x: 50, y: 50 };
    if (els.endpoint) {
      els.endpoint.setAttribute('cx', end.x.toFixed(2));
      els.endpoint.setAttribute('cy', end.y.toFixed(2));
    }
    if (els.previewFrame) els.previewFrame.dataset.motion = Math.abs(throttle) < 0.02 ? 'stopped' : (throttle < 0 ? 'reverse' : 'forward');
  }
  function renderStatus(status = {}) {
    const ap = status.autopilot || status || {};
    const running = Boolean(ap.running);
    lastRunning = running;
    document.body.dataset.autopilotRunning = running ? 'true' : 'false';
    const command = ap.last_command || {};
    const output = ap.last_output || {};
    if (els.runningPill) els.runningPill.textContent = running ? 'running' : 'idle';
    if (els.modePill) els.modePill.textContent = ap.mode_label || ap.mode || 'hold';
    if (els.remainingPill) els.remainingPill.textContent = `${Number(ap.remaining_s || 0).toFixed(1)} s`;
    if (els.dbgRunning) els.dbgRunning.textContent = running ? 'yes' : 'no';
    if (els.dbgSource) els.dbgSource.textContent = 'scripted profile';
    if (els.dbgSteering) els.dbgSteering.textContent = signed(command.steering || 0);
    if (els.dbgThrottle) els.dbgThrottle.textContent = signed(command.throttle || 0);
    if (els.dbgLeft) els.dbgLeft.textContent = signed(output.left || 0);
    if (els.dbgRight) els.dbgRight.textContent = signed(output.right || 0);
    if (els.dbgElapsed) els.dbgElapsed.textContent = `${Number(ap.elapsed_s || 0).toFixed(1)} s`;
    if (els.dbgReason) els.dbgReason.textContent = ap.last_reason || 'idle';
    setCode('status', ap.last_error_code || 'PISD-OK-000');
    renderPath(command);
    if (running) startStatusLoop(); else stopStatusLoop(false);
  }
  async function refreshStatus(silent = false) {
    try {
      const { payload } = await api('GET', '/api/autopilot/status');
      renderStatus(payload.autopilot || {});
      if (!silent) setNotice(payload.autopilot?.last_message || payload.message || 'Autopilot status refreshed.', payload.code);
      writeLog('status', payload.autopilot || payload);
    } catch (err) {
      setNotice(`Autopilot status failed: ${String(err)}`, 'PISD-API-002');
    }
  }
  function startStatusLoop() {
    if (statusTimer) return;
    statusTimer = window.setInterval(() => refreshStatus(true), 600);
  }
  function stopStatusLoop(clear = true) {
    if (!statusTimer) return;
    window.clearInterval(statusTimer);
    statusTimer = 0;
    if (clear) renderPath({ steering: 0, throttle: 0 });
  }
  async function saveConfig() {
    const config = readConfig();
    const { payload } = await api('POST', '/api/autopilot/config', config);
    renderStatus(payload.autopilot || {});
    setNotice(payload.message || 'Autopilot settings saved.', payload.code);
    writeLog('config saved', payload);
  }
  async function startAutopilot() {
    const config = readConfig();
    const body = {
      ...config,
      safety_ack: Boolean(els.safetyAck?.checked),
      enable_autopilot: Boolean(els.safetyAck?.checked),
      enable_motor_output: Boolean(els.enableMotorOutput?.checked),
    };
    const { response, payload } = await api('POST', '/api/autopilot/start', body);
    renderStatus(payload.autopilot || {});
    setNotice(payload.message || (response.ok ? 'Autopilot started.' : 'Autopilot start failed.'), payload.code);
    writeLog('start', payload);
  }
  async function stopAutopilot(reason = 'user_stop') {
    const { payload } = await api('POST', '/api/autopilot/stop', { reason });
    renderStatus(payload.autopilot || {});
    setNotice(payload.message || 'Autopilot stopped.', payload.code);
    writeLog('stop', payload);
  }
  async function startCamera(live = false) {
    const { payload } = await api('POST', '/api/camera/start', {});
    setCode('preview', payload.code);
    if (els.previewImage) els.previewImage.src = live ? `/video_feed?t=${Date.now()}` : `/api/camera/frame.jpg?t=${Date.now()}`;
    if (els.previewFrame) els.previewFrame.dataset.previewMode = live ? 'live' : 'snapshot';
    writeLog(live ? 'live camera' : 'start camera', payload);
  }
  async function stopCamera() {
    const { payload } = await api('POST', '/api/camera/stop', {});
    setCode('preview', payload.code);
    if (els.previewImage) els.previewImage.src = IDLE_SRC;
    if (els.previewFrame) els.previewFrame.dataset.previewMode = 'idle';
    writeLog('stop camera', payload);
  }
  function failSafeStop() {
    if (!lastRunning) return;
    const body = JSON.stringify({ reason: 'page_leave' });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/autopilot/stop', new Blob([body], { type: 'application/json' }));
      } else {
        fetch('/api/autopilot/stop', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, keepalive: true });
      }
    } catch (_err) {}
  }
  for (const element of [els.throttle, els.steerLimit, els.steeringBias, els.duration, els.tickHz]) {
    element?.addEventListener('input', () => { updateLabels(); renderPath(readConfig()); });
  }
  $('apRefresh')?.addEventListener('click', () => refreshStatus(false));
  $('apSaveConfig')?.addEventListener('click', () => saveConfig().catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apStart')?.addEventListener('click', () => startAutopilot().catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apStop')?.addEventListener('click', () => stopAutopilot('user_stop').catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apStopTop')?.addEventListener('click', () => stopAutopilot('top_stop').catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apBigStop')?.addEventListener('click', () => stopAutopilot('big_stop').catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apStartCamera')?.addEventListener('click', () => startCamera(false).catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apLiveCamera')?.addEventListener('click', () => startCamera(true).catch(err => setNotice(String(err), 'PISD-API-002')));
  $('apStopCamera')?.addEventListener('click', () => stopCamera().catch(err => setNotice(String(err), 'PISD-API-002')));
  window.addEventListener('pagehide', failSafeStop);
  window.addEventListener('beforeunload', failSafeStop);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') failSafeStop(); });

  if (els.previewImage) els.previewImage.src = IDLE_SRC;
  const initialAutopilot = initialStatus.autopilot || {};
  applyConfigToControls(initialAutopilot.config || initialStatus.settings?.autopilot || {});
  renderStatus(initialAutopilot);
})();
