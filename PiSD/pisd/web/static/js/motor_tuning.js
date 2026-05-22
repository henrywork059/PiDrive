(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const initial = JSON.parse(($('motorTuningInitialStatus')?.textContent || '{}'));
  const overlayGeometry = window.PiSDOverlayGeometry || null;
  const DEFAULT_OVERLAY = {
    enabled: true,
    path_length_scale: 1.0,
    curve_strength: 3.35,
    opacity: 0.94,
    path_width_scale: 0.34,
    sample_count: 56,
    wheelbase: 0.32,
    max_steer_rad: 0.62,
    curve_response: 1.05,
    curvature_scale: 0.52,
    curvature_limit: 2.25,
    entry_blend_start: 0.76,
    road_half_width: 0.41,
    base_y: 96,
    horizon_y: 31,
    camera_forward_offset: 0.26,
    near_clip: 0.19,
    perspective_scale: 64,
    perspective_depth: 0.92,
    turn_compression: 0.075,
    turn_width_taper: 0.08,
    turn_rate_visual_scale: 2.2,
  };
  const DEFAULT_MOTOR = {
    steering_mode: 'turn_rate',
    steer_mix: 1.0,
    turn_gain: 0.75,
    turn_curve: 1.5,
    min_inside_speed: 0.0,
    allow_pivot_turn: false,
  };

  const controls = {
    globalCode: $('mtunGlobalCode'),
    motorAdapter: $('mtunMotorAdapter'),
    safetyAck: $('mtunSafetyAck'),
    enableMotor: $('mtunEnableMotor'),
    log: $('mtunLog'),
    commandReadout: $('mtunCommandReadout'),
    motorReadout: $('mtunMotorReadout'),
    matchNote: $('mtunMatchNote'),
    overlaySurface: $('mtunOverlaySurface'),
    overlayLeft: $('mtunOverlayLeft'),
    overlayRight: $('mtunOverlayRight'),
    overlayCenter: $('mtunOverlayCenter'),
    overlayStart: $('mtunOverlayStart'),
    overlayEnd: $('mtunOverlayEnd'),
    overlayLabel: $('mtunOverlayLabel'),
    overlayMeta: $('mtunOverlayMeta'),
  };

  const motorFormMap = {
    steering_mode: $('mtunSteeringMode'),
    turn_gain: $('mtunTurnGain'),
    turn_curve: $('mtunTurnCurve'),
    min_inside_speed: $('mtunMinInsideSpeed'),
    steer_mix: $('mtunSteerMix'),
    allow_pivot_turn: $('mtunAllowPivot'),
  };

  const overlayFormMap = {
    turn_rate_visual_scale: $('mtunOverlayTurnRateVisualScale'),
    curve_strength: $('mtunOverlayCurveStrength'),
    curvature_scale: $('mtunOverlayCurvatureScale'),
    curvature_limit: $('mtunOverlayCurvatureLimit'),
    path_length_scale: $('mtunOverlayPathLengthScale'),
    path_width_scale: $('mtunOverlayPathWidthScale'),
    road_half_width: $('mtunOverlayRoadHalfWidth'),
    wheelbase: $('mtunOverlayWheelbase'),
    base_y: $('mtunOverlayBaseY'),
    horizon_y: $('mtunOverlayHorizonY'),
    camera_forward_offset: $('mtunOverlayCameraOffset'),
    perspective_scale: $('mtunOverlayPerspectiveScale'),
    perspective_depth: $('mtunOverlayPerspectiveDepth'),
    turn_compression: $('mtunOverlayTurnCompression'),
    turn_width_taper: $('mtunOverlayTurnWidthTaper'),
    sample_count: $('mtunOverlaySampleCount'),
    opacity: $('mtunOverlayOpacity'),
  };

  let motorSettings = normaliseMotor(initial.motor || initial.settings?.motor || {});
  let overlaySettings = normaliseOverlay(initial.settings?.manual_drive?.overlay || {});
  let lastCommand = { steering: 0, throttle: 0 };
  let lastMotorOutput = { left: 0, right: 0 };
  let requestBusy = false;

  function clamp(value, min, max, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(min, Math.min(max, number)) : fallback;
  }

  function finiteOr(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function fmt(value, digits = 2) {
    const number = Number(value);
    return `${number >= 0 ? '+' : ''}${(Number.isFinite(number) ? number : 0).toFixed(digits)}`;
  }

  function isOk(code) { return String(code || '').startsWith('PISD-OK'); }

  function setCode(target, code) {
    const value = code || 'PISD-OK-000';
    const element = typeof target === 'string' ? document.querySelector(`[data-code-for="${target}"]`) : target;
    if (!element) return;
    element.textContent = value;
    element.dataset.state = isOk(value) ? 'ok' : 'error';
    element.classList.toggle('fail', !isOk(value));
  }

  function setGlobalCode(code) { setCode(controls.globalCode, code); }

  function setBusy(busy) {
    requestBusy = Boolean(busy);
    for (const button of document.querySelectorAll('button')) button.disabled = requestBusy && button.id !== 'mtunStopAll';
  }

  function showLog(label, payload, httpStatus = '') {
    const code = payload?.code || (httpStatus >= 400 ? 'PISD-API-002' : 'PISD-OK-000');
    setGlobalCode(code);
    if (controls.log) controls.log.textContent = JSON.stringify({ label, http_status: httpStatus, response: payload }, null, 2);
  }

  async function api(method, path, body = undefined) {
    const options = { method, headers: {} };
    if (body !== undefined && method !== 'GET') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    const type = response.headers.get('content-type') || '';
    const payload = type.includes('application/json') ? await response.json() : { ok: response.ok, code: response.ok ? 'PISD-OK-000' : 'PISD-API-002', message: await response.text() };
    showLog(`${method} ${path}`, payload, response.status);
    return { response, payload };
  }

  function normaliseMotor(raw = {}) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const mode = String(source.steering_mode || DEFAULT_MOTOR.steering_mode).trim().toLowerCase();
    return {
      steering_mode: mode === 'arcade_mix' ? 'arcade_mix' : 'turn_rate',
      steer_mix: clamp(source.steer_mix, 0, 2, DEFAULT_MOTOR.steer_mix),
      turn_gain: clamp(source.turn_gain, 0, 5, DEFAULT_MOTOR.turn_gain),
      turn_curve: clamp(source.turn_curve, 0.05, 8, DEFAULT_MOTOR.turn_curve),
      min_inside_speed: clamp(source.min_inside_speed, 0, 0.99, DEFAULT_MOTOR.min_inside_speed),
      allow_pivot_turn: typeof source.allow_pivot_turn === 'string'
        ? ['true', '1', 'yes', 'on'].includes(source.allow_pivot_turn.trim().toLowerCase())
        : Boolean(source.allow_pivot_turn ?? DEFAULT_MOTOR.allow_pivot_turn),
    };
  }

  function normaliseOverlay(raw = {}) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const next = { ...DEFAULT_OVERLAY };
    for (const [key, fallback] of Object.entries(DEFAULT_OVERLAY)) {
      if (key === 'enabled') next[key] = typeof source[key] === 'undefined' ? fallback : !['false', '0', 'no', 'off'].includes(String(source[key]).toLowerCase());
      else next[key] = finiteOr(source[key], fallback);
    }
    return next;
  }

  function readNumber(element, fallback = 0) { return finiteOr(element?.value, fallback); }

  function fillMotorForm() {
    for (const [key, element] of Object.entries(motorFormMap)) {
      if (!element) continue;
      if (element.type === 'checkbox') element.checked = Boolean(motorSettings[key]);
      else element.value = String(motorSettings[key]);
    }
  }

  function readMotorForm() {
    const next = { ...motorSettings };
    for (const [key, element] of Object.entries(motorFormMap)) {
      if (!element) continue;
      next[key] = element.type === 'checkbox' ? element.checked : element.value;
    }
    return normaliseMotor(next);
  }

  function fillOverlayForm() {
    for (const [key, element] of Object.entries(overlayFormMap)) {
      if (element) element.value = String(overlaySettings[key]);
    }
  }

  function readOverlayForm() {
    const next = { ...overlaySettings };
    for (const [key, element] of Object.entries(overlayFormMap)) {
      if (!element) continue;
      const number = Number(element.value);
      next[key] = Number.isFinite(number) ? number : DEFAULT_OVERLAY[key];
    }
    return normaliseOverlay(next);
  }

  function localMotorOutput(command) {
    const steering = clamp(command.steering, -1, 1, 0);
    const throttle = clamp(command.throttle, -1, 1, 0);
    if (motorSettings.steering_mode === 'arcade_mix') {
      return {
        left: clamp(throttle - motorSettings.steer_mix * steering, -1, 1, 0),
        right: clamp(throttle + motorSettings.steer_mix * steering, -1, 1, 0),
      };
    }
    const turnIntent = overlayGeometry?.turnRateIntent ? overlayGeometry.turnRateIntent(steering, motorSettings) : Math.sign(steering) * Math.pow(Math.abs(steering), motorSettings.turn_curve) * motorSettings.turn_gain;
    const turnMag = clamp(Math.abs(turnIntent), 0, 1, 0);
    if (turnMag <= 1e-6) return { left: throttle, right: throttle };
    if (motorSettings.allow_pivot_turn && Math.abs(throttle) < 1e-4) return steering > 0 ? { left: turnMag, right: -turnMag } : { left: -turnMag, right: turnMag };
    const insideFactor = motorSettings.allow_pivot_turn ? (1 - 2 * turnMag) : Math.max(motorSettings.min_inside_speed, 1 - turnMag);
    return steering > 0 ? { left: throttle, right: throttle * insideFactor } : { left: throttle * insideFactor, right: throttle };
  }

  function updateReadouts() {
    controls.commandReadout.textContent = `steering ${fmt(lastCommand.steering)} / throttle ${fmt(lastCommand.throttle)}`;
    controls.motorReadout.textContent = `left ${fmt(lastMotorOutput.left)} / right ${fmt(lastMotorOutput.right)}`;
  }

  function commandLabel(command) {
    if (Math.abs(command.throttle) < 0.02 && Math.abs(command.steering) < 0.02) return 'stopped preview';
    const dir = command.throttle < -0.02 ? 'reverse' : command.throttle > 0.02 ? 'forward' : 'pivot';
    if (Math.abs(command.steering) < 0.06) return `${dir} straight`;
    return `${dir} ${command.steering < 0 ? 'left' : 'right'} curve`;
  }

  function drawOverlay(command = lastCommand) {
    lastCommand = { steering: clamp(command.steering, -1, 1, 0), throttle: clamp(command.throttle, -1, 1, 0) };
    lastMotorOutput = localMotorOutput(lastCommand);
    updateReadouts();
    const geometry = overlayGeometry?.roadGuideGeometry ? overlayGeometry.roadGuideGeometry({
      throttle: lastCommand.throttle,
      steering: lastCommand.steering,
      settings: overlaySettings,
      defaults: DEFAULT_OVERLAY,
      motorSettings,
    }) : null;
    if (!geometry) return;
    const opacity = clamp(overlaySettings.opacity, 0, 1, DEFAULT_OVERLAY.opacity);
    if (controls.overlaySurface) {
      controls.overlaySurface.setAttribute('d', geometry.surfacePath || '');
      controls.overlaySurface.style.opacity = String(Math.max(0.10, opacity * 0.42));
    }
    if (controls.overlayLeft) {
      controls.overlayLeft.setAttribute('d', geometry.leftPath || '');
      controls.overlayLeft.style.opacity = String(opacity);
    }
    if (controls.overlayRight) {
      controls.overlayRight.setAttribute('d', geometry.rightPath || '');
      controls.overlayRight.style.opacity = String(opacity);
    }
    if (controls.overlayCenter) {
      controls.overlayCenter.setAttribute('d', geometry.centerPath || '');
      controls.overlayCenter.style.opacity = String(Math.max(0.12, opacity * 0.42));
    }
    if (controls.overlayStart && geometry.start) {
      controls.overlayStart.setAttribute('cx', geometry.start.x.toFixed(2));
      controls.overlayStart.setAttribute('cy', geometry.start.y.toFixed(2));
    }
    if (controls.overlayEnd && geometry.end) {
      controls.overlayEnd.setAttribute('cx', geometry.end.x.toFixed(2));
      controls.overlayEnd.setAttribute('cy', geometry.end.y.toFixed(2));
    }
    if (controls.overlayLabel) controls.overlayLabel.textContent = commandLabel(lastCommand);
    if (controls.overlayMeta) controls.overlayMeta.textContent = `mode ${geometry.steeringMode || motorSettings.steering_mode} · turn ${Math.abs(Number(geometry.turnIntent || 0)).toFixed(2)} · curve ${Number(geometry.curve || 0).toFixed(2)}`;
  }

  function straightCommand(reverse = false) {
    const speed = Math.abs(readNumber($('mtunStraightSpeed'), 0.18));
    return { steering: 0, throttle: reverse ? -speed : speed, duration: readNumber($('mtunStraightDuration'), 0.75), label: reverse ? 'tune_straight_reverse' : 'tune_straight_forward' };
  }

  function turnCommand() {
    const direction = String($('mtunTurnDirection')?.value || 'left');
    const speed = Math.abs(readNumber($('mtunTurnSpeed'), 0.18));
    const turn = Math.abs(readNumber($('mtunTurnAmount'), 0.65));
    return { steering: direction === 'right' ? turn : -turn, throttle: speed, duration: readNumber($('mtunTurnDuration'), 0.75), label: `tune_turn_${direction}` };
  }

  function customCommand() {
    return { steering: readNumber($('mtunCustomSteering'), 0), throttle: readNumber($('mtunCustomThrottle'), 0.18), duration: readNumber($('mtunCustomDuration'), 0.75), label: 'tune_custom_command' };
  }

  async function runTimed(command) {
    const steering = clamp(command.steering, -1, 1, 0);
    const throttle = clamp(command.throttle, -1, 1, 0);
    const duration = clamp(command.duration, 0.05, 10, 0.75);
    drawOverlay({ steering, throttle });
    setBusy(true);
    try {
      const body = {
        steering,
        throttle,
        duration,
        label: command.label,
        safety_ack: Boolean(controls.safetyAck?.checked),
        enable_motor_output: Boolean(controls.enableMotor?.checked),
      };
      const { payload } = await api('POST', '/api/motor/tune-run', body);
      setCode('motion', payload.code || 'PISD-OK-000');
      const tuning = payload.tuning || {};
      if (tuning.left !== undefined && tuning.right !== undefined) {
        lastMotorOutput = { left: Number(tuning.left) || 0, right: Number(tuning.right) || 0 };
        updateReadouts();
      }
      if (payload.motor) {
        motorSettings = normaliseMotor(payload.motor);
        fillMotorForm();
      }
      if (controls.matchNote) controls.matchNote.textContent = payload.ok ? 'Observe the real path, then adjust overlay visual scale/curve if needed.' : 'Run refused or failed; check safety and log.';
    } catch (error) {
      const payload = { ok: false, code: 'PISD-API-002', message: String(error) };
      showLog('runTimed', payload);
      setCode('motion', payload.code);
    } finally {
      setBusy(false);
    }
  }

  async function saveMotorSettings() {
    motorSettings = readMotorForm();
    drawOverlay(lastCommand);
    setBusy(true);
    try {
      const { payload } = await api('POST', '/api/settings/apply', { motor: motorSettings });
      setCode('motor', payload.code || 'PISD-OK-000');
      if (payload.motor) motorSettings = normaliseMotor(payload.motor);
      fillMotorForm();
    } catch (error) {
      const payload = { ok: false, code: 'PISD-API-002', message: String(error) };
      showLog('saveMotorSettings', payload);
      setCode('motor', payload.code);
    } finally {
      setBusy(false);
      drawOverlay(lastCommand);
    }
  }

  async function saveOverlaySettings() {
    overlaySettings = readOverlayForm();
    drawOverlay(lastCommand);
    setBusy(true);
    try {
      const { payload } = await api('POST', '/api/settings/apply', { manual_drive: { overlay: overlaySettings } });
      setCode('overlay-settings', payload.code || 'PISD-OK-000');
      const saved = payload.settings?.manual_drive?.overlay;
      if (saved) overlaySettings = normaliseOverlay(saved);
      fillOverlayForm();
    } catch (error) {
      const payload = { ok: false, code: 'PISD-API-002', message: String(error) };
      showLog('saveOverlaySettings', payload);
      setCode('overlay-settings', payload.code);
    } finally {
      setBusy(false);
      drawOverlay(lastCommand);
    }
  }

  async function refreshStatus() {
    try {
      const { payload } = await api('GET', '/api/status');
      setGlobalCode(payload.code || 'PISD-OK-000');
      if (payload.motor) motorSettings = normaliseMotor(payload.motor);
      if (payload.settings?.manual_drive?.overlay) overlaySettings = normaliseOverlay(payload.settings.manual_drive.overlay);
      if (controls.motorAdapter) controls.motorAdapter.textContent = payload.motor?.adapter || 'unknown';
      fillMotorForm();
      fillOverlayForm();
      drawOverlay(lastCommand);
    } catch (error) {
      showLog('refreshStatus', { ok: false, code: 'PISD-API-002', message: String(error) });
    }
  }

  async function stopAll() {
    try {
      const { payload } = await api('POST', '/api/control/stop', {});
      setGlobalCode(payload.code || 'PISD-OK-000');
      setCode('safety', payload.code || 'PISD-OK-000');
      lastCommand = { steering: 0, throttle: 0 };
      lastMotorOutput = { left: 0, right: 0 };
      drawOverlay(lastCommand);
    } catch (error) {
      showLog('stopAll', { ok: false, code: 'PISD-API-002', message: String(error) });
    }
  }

  function bind() {
    $('mtunRunStraightForward')?.addEventListener('click', () => runTimed(straightCommand(false)));
    $('mtunRunStraightReverse')?.addEventListener('click', () => runTimed(straightCommand(true)));
    $('mtunRunTurn')?.addEventListener('click', () => runTimed(turnCommand()));
    $('mtunRunCustom')?.addEventListener('click', () => runTimed(customCommand()));
    $('mtunApplyMotor')?.addEventListener('click', saveMotorSettings);
    $('mtunApplyOverlay')?.addEventListener('click', saveOverlaySettings);
    $('mtunRefreshStatus')?.addEventListener('click', refreshStatus);
    $('mtunStopAll')?.addEventListener('click', stopAll);
    $('mtunResetOverlay')?.addEventListener('click', () => {
      overlaySettings = normaliseOverlay(DEFAULT_OVERLAY);
      fillOverlayForm();
      drawOverlay(lastCommand);
    });
    for (const element of [...Object.values(motorFormMap), ...Object.values(overlayFormMap), $('mtunTurnDirection'), $('mtunTurnSpeed'), $('mtunTurnAmount'), $('mtunStraightSpeed'), $('mtunCustomSteering'), $('mtunCustomThrottle')]) {
      element?.addEventListener('input', () => {
        motorSettings = readMotorForm();
        overlaySettings = readOverlayForm();
        let command = lastCommand;
        if (document.activeElement && ['mtunTurnDirection', 'mtunTurnSpeed', 'mtunTurnAmount'].includes(document.activeElement.id)) command = turnCommand();
        if (document.activeElement && ['mtunStraightSpeed'].includes(document.activeElement.id)) command = straightCommand(false);
        if (document.activeElement && ['mtunCustomSteering', 'mtunCustomThrottle'].includes(document.activeElement.id)) command = customCommand();
        drawOverlay(command);
      });
    }
  }

  fillMotorForm();
  fillOverlayForm();
  bind();
  drawOverlay({ steering: -0.45, throttle: 0.18 });
  refreshStatus();
})();
