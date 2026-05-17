(() => {
  'use strict';

  const $ = id => document.getElementById(id);
  const initialStatus = JSON.parse($('manualDriveInitialStatus')?.textContent || '{}');
  const LEGACY_STORAGE_KEY = 'pisd.manualDrive.v1';
  const SETTINGS_STORAGE_KEY = 'pisd.runtimeSettings.v2';
  const DEFAULTS = {
    speed: 0.18,
    max_speed_limit: 1.0,
    steer_strength: 1.0,
    drag_send_interval_ms: 90,
    recording_fps: 6,
    overlay: {
      enabled: true,
      path_length_scale: 1.0,
      curve_strength: 1.0,
      opacity: 0.92,
      path_width_scale: 1.0,
    },
  };
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
  const recordingIndicator = $('mdrvRecordingIndicator');
  const captureNotice = $('mdrvCaptureNotice');
  const fileKind = $('mdrvFileKind');
  const fileSelect = $('mdrvFileSelect');
  const filesNotice = $('mdrvFilesNotice');
  const intentOut = $('mdrvIntentOut');
  const motorOut = $('mdrvMotorOut');
  const previewFrame = $('mdrvPreviewFrame');
  const overlayToggle = $('mdrvOverlayToggle');
  const overlayMode = $('mdrvOverlayMode');
  const overlayCar = $('mdrvOverlayCar');
  const overlayPath = $('mdrvOverlayPath');
  const overlayPathWide = $('mdrvOverlayPathWide');
  const overlayPathGuide = $('mdrvOverlayPathGuide');
  const overlayEndpoint = $('mdrvOverlayEndpoint');
  const overlayCurveLabel = $('mdrvOverlayCurveLabel');
  const overlayThrottleFill = $('mdrvOverlayThrottleFill');
  const overlaySteeringFill = $('mdrvOverlaySteeringFill');
  const overlayThrottleValue = $('mdrvOverlayThrottleValue');
  const overlaySteeringValue = $('mdrvOverlaySteeringValue');
  const overlayLeftValue = $('mdrvOverlayLeftValue');
  const overlayRightValue = $('mdrvOverlayRightValue');
  const driveDebugPanel = $('mdrvDriveDebugPanel');
  const overlayDebugSource = $('mdrvOverlayDebugSource');
  const overlayDebugSteering = $('mdrvOverlayDebugSteering');
  const overlayDebugThrottle = $('mdrvOverlayDebugThrottle');
  const overlayDebugLeft = $('mdrvOverlayDebugLeft');
  const overlayDebugRight = $('mdrvOverlayDebugRight');
  const overlayLengthScale = $('mdrvOverlayLengthScale');
  const overlayCurveScale = $('mdrvOverlayCurveScale');
  const overlayOpacity = $('mdrvOverlayOpacity');
  const overlayPathWidth = $('mdrvOverlayPathWidth');
  const overlayLengthScaleOut = $('mdrvOverlayLengthScaleOut');
  const overlayCurveScaleOut = $('mdrvOverlayCurveScaleOut');
  const overlayOpacityOut = $('mdrvOverlayOpacityOut');
  const overlayPathWidthOut = $('mdrvOverlayPathWidthOut');
  let dragging = false;
  let lastSentAt = 0;
  let lastPayload = { steering: 0, throttle: 0, steer_mix: 1.0 };
  let lastMotorOutput = { left: 0, right: 0 };
  let recordingRunning = Boolean(initialStatus.recording?.running);
  let recordingCollections = { recordings: [], snapshots: [] };
  let currentPreviewMode = "snapshot";
  let overlaySettings = { ...DEFAULTS.overlay };
  let overlayPersistTimer = 0;
  let lastOverlaySource = 'stopped';

  function isOk(code) { return String(code || '').startsWith('PISD-OK'); }
  function clamp(value, min, max, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
  }
  function maxSpeedLimit() {
    return clamp(readRuntimeLocal().manual_drive?.max_speed_limit || DEFAULTS.max_speed_limit, 0.1, 1.0, DEFAULTS.max_speed_limit);
  }
  function setCode(target, code) {
    const value = code || 'PISD-OK-000';
    const element = typeof target === 'string' ? document.querySelector(`[data-code-for="${target}"]`) : target;
    if (!element) return;
    element.textContent = value;
    element.dataset.state = isOk(value) ? 'ok' : 'error';
  }
  function setGlobalCode(code) { setCode(globalCode, code); }

  function shortPath(value) {
    const text = String(value || '');
    if (text.length <= 72) return text;
    return `...${text.slice(-69)}`;
  }

  function setShortStatus(message, code = 'PISD-OK-000') {
    const short = $('mdrvShortStatus');
    if (short) {
      short.textContent = message;
      short.dataset.state = isOk(code) ? 'ok' : 'error';
    }
    setGlobalCode(code);
  }

  function showCaptureNotice(message, code = 'PISD-OK-000') {
    if (!captureNotice) return;
    captureNotice.textContent = message;
    captureNotice.dataset.state = isOk(code) ? 'ok' : 'error';
    captureNotice.classList.add('is-visible');
    setShortStatus(message, code);
  }

  function showFilesNotice(message, code = 'PISD-OK-000') {
    if (filesNotice) filesNotice.textContent = message;
    setCode('files', code);
  }

  function formatSigned(value) {
    const n = Number(value);
    const safe = Number.isFinite(n) ? Math.max(-1, Math.min(1, n)) : 0;
    return `${safe >= 0 ? '+' : ''}${safe.toFixed(2)}`;
  }

  function overlaySourceText(command, output, sourceHint = 'manual intent') {
    const steering = Math.abs(Number(command?.steering || 0));
    const throttle = Math.abs(Number(command?.throttle || 0));
    const left = Math.abs(Number(output?.left || 0));
    const right = Math.abs(Number(output?.right || 0));
    if (steering < 0.02 && throttle < 0.02 && left < 0.02 && right < 0.02) return 'stopped';
    return sourceHint || 'manual intent';
  }

  function renderOverlayDebug(command, output, sourceHint = 'manual intent') {
    const source = overlaySourceText(command, output, sourceHint);
    lastOverlaySource = source;
    if (driveDebugPanel) driveDebugPanel.dataset.overlaySource = source.replace(/\s+/g, '-');
    if (overlayDebugSource) overlayDebugSource.textContent = source;
    if (overlayDebugSteering) overlayDebugSteering.textContent = formatSigned(command?.steering || 0);
    if (overlayDebugThrottle) overlayDebugThrottle.textContent = formatSigned(command?.throttle || 0);
    if (overlayDebugLeft) overlayDebugLeft.textContent = formatSigned(output?.left || 0);
    if (overlayDebugRight) overlayDebugRight.textContent = formatSigned(output?.right || 0);
    if (previewFrame) previewFrame.dataset.overlaySource = source.replace(/\s+/g, '-');
    return source;
  }

  function renderMotorSignals(command = lastPayload, output = lastMotorOutput, sourceHint = 'manual intent') {
    const steering = Number(command?.steering || 0);
    const throttle = Number(command?.throttle || 0);
    const left = Number(output?.left || 0);
    const right = Number(output?.right || 0);
    const source = renderOverlayDebug({ steering, throttle }, { left, right }, sourceHint);
    if (intentOut) intentOut.textContent = `S ${formatSigned(steering)} / T ${formatSigned(throttle)}`;
    if (motorOut) motorOut.textContent = `L ${formatSigned(left)} / R ${formatSigned(right)}`;
    updateDriveOverlay({ steering, throttle, steer_mix: command?.steer_mix ?? 1.0 }, { left, right }, source);
  }


  function normaliseOverlaySettings(raw = {}) {
    const source = raw && typeof raw === 'object' ? raw : {};
    return {
      enabled: String(source.enabled ?? DEFAULTS.overlay.enabled).toLowerCase() !== 'false' && !['0', 'no', 'off'].includes(String(source.enabled ?? DEFAULTS.overlay.enabled).toLowerCase()),
      path_length_scale: clamp(source.path_length_scale ?? DEFAULTS.overlay.path_length_scale, 0.5, 1.8, DEFAULTS.overlay.path_length_scale),
      curve_strength: clamp(source.curve_strength ?? DEFAULTS.overlay.curve_strength, 0.4, 1.8, DEFAULTS.overlay.curve_strength),
      opacity: clamp(source.opacity ?? DEFAULTS.overlay.opacity, 0.2, 1.0, DEFAULTS.overlay.opacity),
      path_width_scale: clamp(source.path_width_scale ?? DEFAULTS.overlay.path_width_scale, 0.6, 1.8, DEFAULTS.overlay.path_width_scale),
    };
  }

  function updateOverlaySettingLabels() {
    if (overlayLengthScaleOut) overlayLengthScaleOut.textContent = overlaySettings.path_length_scale.toFixed(2);
    if (overlayCurveScaleOut) overlayCurveScaleOut.textContent = overlaySettings.curve_strength.toFixed(2);
    if (overlayOpacityOut) overlayOpacityOut.textContent = overlaySettings.opacity.toFixed(2);
    if (overlayPathWidthOut) overlayPathWidthOut.textContent = overlaySettings.path_width_scale.toFixed(2);
  }

  function applyOverlayCalibration(settings = overlaySettings, persist = false) {
    overlaySettings = normaliseOverlaySettings(settings);
    if (overlayLengthScale) overlayLengthScale.value = overlaySettings.path_length_scale;
    if (overlayCurveScale) overlayCurveScale.value = overlaySettings.curve_strength;
    if (overlayOpacity) overlayOpacity.value = overlaySettings.opacity;
    if (overlayPathWidth) overlayPathWidth.value = overlaySettings.path_width_scale;
    if (previewFrame) previewFrame.style.setProperty('--mdrv-overlay-calibrated-opacity', String(overlaySettings.opacity));
    updateOverlaySettingLabels();
    setOverlayEnabled(overlaySettings.enabled, false);
    updateDriveOverlay(lastPayload, lastMotorOutput, lastOverlaySource);
    if (persist) persistOverlaySettingsSoon();
  }

  function readOverlayCalibrationFromControls() {
    return normaliseOverlaySettings({
      ...overlaySettings,
      path_length_scale: overlayLengthScale?.value,
      curve_strength: overlayCurveScale?.value,
      opacity: overlayOpacity?.value,
      path_width_scale: overlayPathWidth?.value,
    });
  }

  function setSignedFill(element, value) {
    if (!element) return;
    const number = clamp(value, -1, 1, 0);
    element.style.left = number < 0 ? `${50 + (number * 50)}%` : '50%';
    element.style.width = `${Math.abs(number) * 50}%`;
  }

  function driveModeText(throttle, steering) {
    const throttleAbs = Math.abs(throttle);
    const steeringAbs = Math.abs(steering);
    if (throttleAbs < 0.02 && steeringAbs < 0.02) return 'STOPPED';
    const direction = throttle < -0.02 ? 'REV' : throttle > 0.02 ? 'FWD' : 'TURN';
    if (steeringAbs < 0.08) return direction;
    return `${direction} ${steering < 0 ? 'LEFT' : 'RIGHT'}`;
  }

  function curveLabelText(throttle, steering) {
    const throttleAbs = Math.abs(throttle);
    const steeringAbs = Math.abs(steering);
    if (throttleAbs < 0.02 && steeringAbs < 0.02) return 'hold';
    if (steeringAbs < 0.06) return 'straight';
    const tightness = steeringAbs > 0.72 ? 'tight' : steeringAbs > 0.38 ? 'medium' : 'gentle';
    const turn = steering < 0 ? 'left' : 'right';
    return `${tightness} ${turn}`;
  }

  function pointsToPath(points) {
    if (!Array.isArray(points) || !points.length) return '';
    return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`).join(' ');
  }

  function sampledIntendedPath(throttle, steering) {
    const safeThrottle = clamp(throttle, -1, 1, 0);
    const safeSteering = clamp(steering, -1, 1, 0);
    const speed = Math.abs(safeThrottle);
    const movingReverse = safeThrottle < -0.02;
    const startX = 50;
    const startY = movingReverse ? 68 : 88;
    const samples = 34;
    const horizonScale = overlaySettings.path_length_scale || 1.0;
    const horizon = (movingReverse ? (14 + speed * 30) : (22 + speed * 62)) * horizonScale;

    // 0.4.6: draw a sampled constant-curvature path rather than a single
    // quadratic curve. This is a screen-space bicycle/Ackermann approximation:
    // throttle controls horizon length; steering controls curvature. Reverse is
    // mirrored so the driver sees where the car will back toward.
    const visualWheelbase = 34;
    const maxSteerRad = 0.72 * (overlaySettings.curve_strength || 1.0);
    const visualSteering = movingReverse ? -safeSteering : safeSteering;
    const curvature = Math.tan(visualSteering * maxSteerRad) / visualWheelbase;
    const signedDistance = movingReverse ? -horizon : horizon;
    const points = [];
    for (let i = 0; i <= samples; i += 1) {
      const s = signedDistance * (i / samples);
      let lateral = 0;
      let longitudinal = s;
      if (Math.abs(curvature) > 0.0008) {
        lateral = (1 - Math.cos(curvature * s)) / curvature;
        longitudinal = Math.sin(curvature * s) / curvature;
      }
      points.push({ x: startX + lateral, y: startY - longitudinal });
    }
    return { points, curvature, movingReverse, speed };
  }

  function drawIntendedPath(throttle, steering) {
    if (!overlayPath) return;
    const safeThrottle = clamp(throttle, -1, 1, 0);
    const safeSteering = clamp(steering, -1, 1, 0);
    const steeringAbs = Math.abs(safeSteering);
    const moving = Math.abs(safeThrottle) >= 0.02;
    const { points, curvature, movingReverse, speed } = sampledIntendedPath(safeThrottle, safeSteering);
    const pathD = pointsToPath(points);
    const end = points[points.length - 1] || { x: 50, y: 88 };
    const calibratedOpacity = overlaySettings.opacity || DEFAULTS.overlay.opacity;
    const opacity = moving || steeringAbs >= 0.02 ? String(calibratedOpacity) : String(Math.max(0.18, calibratedOpacity * 0.32));
    const widthScale = overlaySettings.path_width_scale || 1.0;
    const strokeWidth = String((2.4 + speed * 3.2) * widthScale);
    for (const pathElement of [overlayPathWide, overlayPathGuide, overlayPath]) {
      if (!pathElement) continue;
      pathElement.setAttribute('d', pathD);
      pathElement.style.opacity = opacity;
      pathElement.style.strokeDasharray = movingReverse ? '7 5' : 'none';
    }
    if (overlayPathWide) overlayPathWide.style.strokeWidth = String(10 * widthScale);
    if (overlayPathGuide) overlayPathGuide.style.strokeWidth = String(6.2 * widthScale);
    overlayPath.style.strokeWidth = strokeWidth;
    if (overlayEndpoint) {
      overlayEndpoint.setAttribute('cx', end.x.toFixed(2));
      overlayEndpoint.setAttribute('cy', end.y.toFixed(2));
      overlayEndpoint.style.opacity = opacity;
    }
    if (overlayCurveLabel) {
      const curve = Math.abs(curvature) < 0.001 ? 'straight' : `curve ${Math.abs(curvature).toFixed(3)}`;
      overlayCurveLabel.textContent = `${curveLabelText(safeThrottle, safeSteering)} · ${curve}`;
    }
    if (previewFrame) {
      previewFrame.dataset.overlayMotion = moving ? (movingReverse ? 'reverse' : 'forward') : 'stopped';
    }
  }

  function updateDriveOverlay(command = lastPayload, output = lastMotorOutput, sourceHint = 'manual intent') {
    const steering = clamp(command?.steering ?? 0, -1, 1, 0);
    const throttle = clamp(command?.throttle ?? 0, -1, 1, 0);
    const left = clamp(output?.left ?? 0, -1, 1, 0);
    const right = clamp(output?.right ?? 0, -1, 1, 0);
    const moving = Math.abs(throttle) >= 0.02;
    const source = renderOverlayDebug({ steering, throttle }, { left, right }, sourceHint);
    if (overlayMode) overlayMode.textContent = source === 'stopped' ? 'STOPPED' : driveModeText(throttle, steering);
    if (overlayThrottleValue) overlayThrottleValue.textContent = formatSigned(throttle);
    if (overlaySteeringValue) overlaySteeringValue.textContent = formatSigned(steering);
    if (overlayLeftValue) overlayLeftValue.textContent = formatSigned(left);
    if (overlayRightValue) overlayRightValue.textContent = formatSigned(right);
    setSignedFill(overlayThrottleFill, throttle);
    setSignedFill(overlaySteeringFill, steering);
    if (overlayCar) {
      overlayCar.style.transform = `translateX(-50%) rotate(${(steering * 28).toFixed(1)}deg)`;
      overlayCar.style.opacity = moving || Math.abs(steering) >= 0.02 ? '1' : '0.78';
    }
    drawIntendedPath(throttle, steering);
  }

  function setOverlayEnabled(enabled, persist = true) {
    overlaySettings.enabled = Boolean(enabled);
    if (!previewFrame || !overlayToggle) return;
    previewFrame.classList.toggle('mdrv-overlay-enabled', overlaySettings.enabled);
    overlayToggle.textContent = overlaySettings.enabled ? 'Overlay: On' : 'Overlay: Off';
    overlayToggle.setAttribute('aria-pressed', overlaySettings.enabled ? 'true' : 'false');
    overlayToggle.dataset.state = overlaySettings.enabled ? 'on' : 'off';
    if (persist) persistOverlaySettingsSoon();
  }

  function renderMotorSignalsFromStatus(status) {
    const motor = status?.motor || {};
    const hasServerCommand = motor.last_command && typeof motor.last_command === 'object';
    let command = hasServerCommand ? motor.last_command : lastPayload;
    const output = { left: motor.last_left ?? lastMotorOutput.left, right: motor.last_right ?? lastMotorOutput.right };
    if (!hasServerCommand && Math.abs(Number(output.left || 0)) < 0.02 && Math.abs(Number(output.right || 0)) < 0.02) {
      command = { steering: 0, throttle: 0, steer_mix: lastPayload.steer_mix || 1.0 };
    }
    lastPayload = {
      steering: Number(command.steering || 0),
      throttle: Number(command.throttle || 0),
      steer_mix: Number(command.steer_mix || lastPayload.steer_mix || 1.0),
    };
    lastMotorOutput = { left: Number(output.left || 0), right: Number(output.right || 0) };
    renderMotorSignals(lastPayload, lastMotorOutput, 'live status');
  }

  function renderMotorSignalsFromApiResponse(payload, fallbackCommand = lastPayload) {
    const motor = payload?.motor || {};
    const command = motor.last_command || fallbackCommand || lastPayload;
    const output = {
      left: payload?.left ?? motor.last_left ?? lastMotorOutput.left,
      right: payload?.right ?? motor.last_right ?? lastMotorOutput.right,
    };
    lastPayload = {
      steering: Number(command.steering ?? fallbackCommand?.steering ?? 0),
      throttle: Number(command.throttle ?? fallbackCommand?.throttle ?? 0),
      steer_mix: Number(command.steer_mix ?? fallbackCommand?.steer_mix ?? 1.0),
    };
    lastMotorOutput = { left: Number(output.left || 0), right: Number(output.right || 0) };
    renderMotorSignals(lastPayload, lastMotorOutput, 'live status');
  }

  function selectedFileItem() {
    const kind = fileKind?.value || 'recording';
    const id = fileSelect?.value || '';
    const list = kind === 'snapshot' ? recordingCollections.snapshots : recordingCollections.recordings;
    const item = list.find(entry => entry.id === id) || null;
    return { kind, id, item };
  }

  function renderFileOptions() {
    if (!fileSelect) return;
    const kind = fileKind?.value || 'recording';
    const list = kind === 'snapshot' ? recordingCollections.snapshots : recordingCollections.recordings;
    fileSelect.innerHTML = '';
    if (!list.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = kind === 'snapshot' ? 'No snapshot folders' : 'No recording folders';
      fileSelect.appendChild(option);
      showFilesNotice(kind === 'snapshot' ? 'No snapshot folders found.' : 'No recording folders found.');
      return;
    }
    for (const item of list) {
      const option = document.createElement('option');
      option.value = item.id;
      const count = Number(item.frame_count || 0);
      const sizeKb = Math.round(Number(item.bytes || 0) / 1024);
      option.textContent = `${item.date || ''}  ${item.label || item.id}  (${count} frames, ${sizeKb} KB)`;
      fileSelect.appendChild(option);
    }
    const selected = selectedFileItem().item || list[0];
    showFilesNotice(`Selected ${kind}: ${selected.id || selected.label || 'folder'}`);
  }

  async function refreshRecordingItems() {
    try {
      const { payload } = await api('GET', '/api/recording/items', undefined, 'files');
      const collections = payload.collections || {};
      recordingCollections = {
        recordings: collections.recordings || [],
        snapshots: collections.snapshots || [],
      };
      renderFileOptions();
      showFilesNotice(`Loaded ${recordingCollections.recordings.length} recordings and ${recordingCollections.snapshots.length} snapshot folders.`, payload.code);
    } catch (err) {
      showFilesNotice(`Folder list failed: ${String(err)}`, 'PISD-REC-007');
      writeLog('recording items failed', { ok: false, code: 'PISD-REC-007', message: String(err) });
    }
  }

  function downloadSelectedZip() {
    const { kind, id } = selectedFileItem();
    if (!id) {
      showFilesNotice('Select a folder before downloading.', 'PISD-REC-008');
      return;
    }
    const url = `/api/recording/download.zip?kind=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}`;
    showFilesNotice(`Preparing ${kind} zip: ${id}`, 'PISD-OK-000');
    window.location.href = url;
  }

  async function deleteSelectedFolder() {
    const { kind, id, item } = selectedFileItem();
    if (!id) {
      showFilesNotice('Select a folder before deleting.', 'PISD-REC-008');
      return;
    }
    const label = item?.label || id;
    const ok = window.confirm(`Delete ${kind} folder?\n\n${label}\n${id}\n\nThis cannot be undone.`);
    if (!ok) return;
    try {
      const { payload } = await api('POST', '/api/recording/delete', { kind, id }, 'files');
      showFilesNotice(payload.ok ? `Deleted ${kind}: ${id}` : `Delete failed: ${payload.code}`, payload.code);
      await refreshRecordingItems();
    } catch (err) {
      showFilesNotice(`Delete failed: ${String(err)}`, 'PISD-REC-009');
      writeLog('recording delete failed', { ok: false, code: 'PISD-REC-009', message: String(err) });
    }
  }

  function updateRecordingIndicator(running) {
    if (!recordingIndicator) return;
    recordingIndicator.dataset.recording = running ? 'on' : 'off';
    recordingIndicator.textContent = running ? 'REC on' : 'REC off';
  }

  function readRuntimeLocal() {
    try { return JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || '{}') || {}; }
    catch (_err) { return {}; }
  }

  function mergeSettingsObjects(base, partial) {
    const result = { ...(base || {}) };
    for (const [key, value] of Object.entries(partial || {})) {
      if (value && typeof value === 'object' && !Array.isArray(value) && result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])) {
        result[key] = mergeSettingsObjects(result[key], value);
      } else {
        result[key] = value;
      }
    }
    return result;
  }

  function writeRuntimeLocal(partial) {
    const current = readRuntimeLocal();
    const next = mergeSettingsObjects(current, { ...partial, saved_at: new Date().toISOString() });
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
    const limit = clamp(serverManual.max_speed_limit || DEFAULTS.max_speed_limit, 0.1, 1.0, DEFAULTS.max_speed_limit);
    const legacySteer = Number(legacy.steer);
    const steerCandidate = (Number.isFinite(legacySteer) && legacySteer !== 0.9)
      ? legacySteer
      : (serverManual.steer_strength ?? DEFAULTS.steer_strength);
    const manual = {
      ...DEFAULTS,
      ...serverManual,
      max_speed_limit: limit,
      speed: clamp(legacy.speed || serverManual.speed || DEFAULTS.speed, 0.0, limit, DEFAULTS.speed),
      steer_strength: clamp(steerCandidate, 0.0, 1.0, DEFAULTS.steer_strength),
      overlay: normaliseOverlaySettings(serverManual.overlay || DEFAULTS.overlay),
    };
    if (speed) { speed.max = String(manual.max_speed_limit); speed.value = manual.speed; }
    if (steer) steer.value = manual.steer_strength;
    applyOverlayCalibration(manual.overlay, false);
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
      overlay: normaliseOverlaySettings(overlaySettings),
    };
    writeRuntimeLocal({ manual_drive });
    localStorage.setItem(LEGACY_STORAGE_KEY, JSON.stringify({ speed: String(manual_drive.speed), steer: String(manual_drive.steer_strength) }));
    try {
      await fetch('/api/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ manual_drive }) });
    } catch (_err) {}
  }

  function persistOverlaySettingsSoon() {
    overlaySettings = normaliseOverlaySettings(overlaySettings);
    writeRuntimeLocal({ manual_drive: { overlay: overlaySettings } });
    window.clearTimeout(overlayPersistTimer);
    overlayPersistTimer = window.setTimeout(() => {
      fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manual_drive: { overlay: overlaySettings } }),
      }).catch(() => {});
    }, 250);
  }

  function writeLog(action, payload, httpStatus = '') {
    const code = payload?.code || (httpStatus >= 400 ? 'PISD-API-002' : 'PISD-OK-000');
    setGlobalCode(code);
    setCode('log', code);
    if (log) log.textContent = JSON.stringify({ action, http_status: httpStatus, response: payload }, null, 2);
    setShortStatus(`${action}: ${code} ${payload?.message || ''}`.trim(), code);
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
    updateRecordingIndicator(rec);
    renderMotorSignalsFromStatus(status);
    setCode('status', status.code || 'PISD-OK-000');
    setGlobalCode(status.code || 'PISD-OK-000');
  }

  async function refreshStatus(userVisible = false) {
    try {
      const { payload } = await api('GET', '/api/status', undefined, 'status');
      renderStatus(payload);
      if (userVisible) {
        if (currentPreviewMode === 'snapshot') snapshotView();
        setShortStatus(`Status refreshed: ${payload?.code || 'PISD-OK-000'}`, payload?.code || 'PISD-OK-000');
        await refreshRecordingItems();
      }
    } catch (err) {
      writeLog('refresh status failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function updateSliderLabels() {
    const limit = maxSpeedLimit();
    if (speed) { speed.max = String(limit); if (Number(speed.value) > limit) speed.value = String(limit); }
    if (steer) { steer.max = '1.0'; if (Number(steer.value) > 1) steer.value = '1.0'; }
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
    renderMotorSignals(payload, lastMotorOutput, 'manual intent');
    try {
      const result = await api('POST', '/api/control/manual', payload, 'drive');
      renderMotorSignalsFromApiResponse(result.payload, payload);
    }
    catch (err) { writeLog('manual drag failed', { ok: false, code: 'PISD-API-002', message: String(err) }); }
  }

  async function stopAll(target = 'stop') {
    setKnob(0, 0);
    lastPayload = { steering: 0, throttle: 0, steer_mix: 1.0 };
    lastMotorOutput = { left: 0, right: 0 };
    renderMotorSignals(lastPayload, lastMotorOutput, 'stopped');
    try {
      const { payload } = await api('POST', '/api/control/stop', {}, target);
      renderMotorSignalsFromApiResponse(payload, lastPayload);
      setShortStatus(`STOP sent: ${payload?.code || 'PISD-OK-000'} ${payload?.message || ''}`.trim(), payload?.code || 'PISD-OK-000');
      await refreshStatus();
    } catch (err) {
      writeLog('STOP failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function livePreview() {
    currentPreviewMode = 'live';
    if (preview) preview.src = `/video_feed?t=${Date.now()}`;
    setShortStatus('Live MJPEG preview selected.', 'PISD-OK-000');
  }

  function snapshotView() {
    currentPreviewMode = 'snapshot';
    if (preview) preview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
    setShortStatus('Snapshot preview refreshed.', 'PISD-OK-000');
  }

  async function startCameraOnly() {
    try {
      const { payload } = await api('POST', '/api/camera/start', {}, 'camera');
      setShortStatus(`Camera start: ${payload?.code || 'PISD-OK-000'} ${payload?.message || ''}`.trim(), payload?.code || 'PISD-OK-000');
      if (currentPreviewMode === 'snapshot') snapshotView();
      await refreshStatus();
    } catch (err) {
      writeLog('start camera failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  async function startLiveCamera() {
    try {
      const { payload } = await api('POST', '/api/camera/start', {}, 'camera');
      livePreview();
      setShortStatus(`Live stream: ${payload?.code || 'PISD-OK-000'} ${payload?.message || ''}`.trim(), payload?.code || 'PISD-OK-000');
      await refreshStatus();
    } catch (err) {
      writeLog('live camera failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  async function captureFrame() {
    try {
      const { payload } = await api('POST', '/api/recording/capture', { label: 'manual_capture' }, 'camera');
      const record = payload?.record || {};
      if (payload?.ok) {
        const file = record.relative_file || record.file || '';
        showCaptureNotice(`Frame captured: ${record.frame_id || 'saved'} ${file ? '(' + shortPath(file) + ')' : ''}`, payload.code);
      } else {
        showCaptureNotice(`Capture failed: ${payload?.code || 'PISD-REC-002'}`, payload?.code || 'PISD-REC-002');
      }
      await refreshStatus();
      await refreshRecordingItems();
    } catch (err) {
      showCaptureNotice(`Capture failed: ${String(err)}`, 'PISD-REC-002');
      writeLog('capture frame failed', { ok: false, code: 'PISD-REC-002', message: String(err) });
    }
  }

  async function toggleRecording() {
    const manual = readRuntimeLocal().manual_drive || {};
    try {
      if (recordingRunning) {
        const { payload } = await api('POST', '/api/recording/stop', {}, 'camera');
        showCaptureNotice(`Recording stopped: ${payload?.code || 'PISD-OK-000'}`, payload?.code || 'PISD-OK-000');
      } else {
        const { payload } = await api('POST', '/api/recording/start', { label: 'manual_drive', fps: manual.recording_fps || DEFAULTS.recording_fps }, 'camera');
        const session = payload?.recording?.active_session || {};
        showCaptureNotice(`Recording started${session.session_id ? ': ' + session.session_id : ''}`, payload?.code || 'PISD-OK-000');
      }
      await refreshStatus();
      await refreshRecordingItems();
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
    $('mdrvRefresh')?.addEventListener('click', () => refreshStatus(true));
    $('mdrvStartCamera')?.addEventListener('click', startCameraOnly);
    $('mdrvLiveCamera')?.addEventListener('click', startLiveCamera);
    $('mdrvCaptureFrame')?.addEventListener('click', captureFrame);
    recordButton?.addEventListener('click', toggleRecording);
    $('mdrvStopTop')?.addEventListener('click', () => stopAll('stop'));
    $('mdrvStopPad')?.addEventListener('click', () => stopAll('drive'));
    $('mdrvStopBig')?.addEventListener('click', () => stopAll('stop'));
    overlayToggle?.addEventListener('click', () => setOverlayEnabled(!previewFrame?.classList.contains('mdrv-overlay-enabled'), true));
    for (const control of [overlayLengthScale, overlayCurveScale, overlayOpacity, overlayPathWidth]) {
      control?.addEventListener('input', () => applyOverlayCalibration(readOverlayCalibrationFromControls(), true));
    }
    $('mdrvRefreshFiles')?.addEventListener('click', refreshRecordingItems);
    $('mdrvDownloadZip')?.addEventListener('click', downloadSelectedZip);
    $('mdrvDeleteFolder')?.addEventListener('click', deleteSelectedFolder);
    fileKind?.addEventListener('change', renderFileOptions);
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
  renderMotorSignals(lastPayload, lastMotorOutput, 'stopped');
  renderStatus(initialStatus);
  bind();
  applyOverlayCalibration(overlaySettings, false);
  updateDriveOverlay(lastPayload, lastMotorOutput, 'stopped');
  updateLock();
  loadSettings();
  refreshRecordingItems();
})();
