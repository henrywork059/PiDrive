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
      // PiSD_0_5_9: road-edge guide defaults. Visual-only; no motor output change. reverse guide hidden.
      curve_strength: 3.35,
      opacity: 0.94,
      path_width_scale: 0.34,
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
  const fileSummary = $('mdrvFileSummary');
  const fileSummaryName = $('mdrvFileSummaryName');
  const fileSummaryFrames = $('mdrvFileSummaryFrames');
  const fileSummarySize = $('mdrvFileSummarySize');
  const fileSummaryModified = $('mdrvFileSummaryModified');
  const fileSummaryId = $('mdrvFileSummaryId');
  const fileSummaryZip = $('mdrvFileSummaryZip');
  const downloadZipButton = $('mdrvDownloadZip');
  const deleteFolderButton = $('mdrvDeleteFolder');
  const intentOut = $('mdrvIntentOut');
  const motorOut = $('mdrvMotorOut');
  const previewFrame = $('mdrvPreviewFrame');
  const overlayToggle = $('mdrvOverlayToggle');
  const overlayMode = $('mdrvOverlayMode');
  const overlayCar = $('mdrvOverlayCar');
  const overlayPath = $('mdrvOverlayPath');
  const overlaySurface = $('mdrvOverlaySurface');
  const overlayPathWide = $('mdrvOverlayPathWide');
  const overlayPathGuide = $('mdrvOverlayPathGuide');
  const overlayEndpoint = $('mdrvOverlayEndpoint');
  const overlayStartPoint = $('mdrvOverlayStartPoint');
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
  const previewModeDebug = $('mdrvPreviewModeDebug');
  const previewCameraDebug = $('mdrvPreviewCameraDebug');
  const previewAgeDebug = $('mdrvPreviewAgeDebug');
  const previewFpsDebug = $('mdrvPreviewFpsDebug');
  const previewLoopDebug = $('mdrvPreviewLoopDebug');
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
  const STOP_COMMAND = { steering: 0, throttle: 0 };
  const STOP_OUTPUT = { left: 0, right: 0 };
  let lastPayload = { ...STOP_COMMAND };
  let lastMotorOutput = { ...STOP_OUTPUT };
  let recordingRunning = Boolean(initialStatus.recording?.running);
  let recordingCollections = { recordings: [], snapshots: [] };
  const PREVIEW_STALE_MS = 2500;
  const PREVIEW_METRICS_MS = 850;
  const PREVIEW_IDLE_SRC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'%3E%3Crect width='1280' height='720' fill='%23020617'/%3E%3Ctext x='640' y='340' fill='%2394a3b8' font-family='Arial,sans-serif' font-size='42' text-anchor='middle'%3EPreview idle%3C/text%3E%3Ctext x='640' y='398' fill='%2364748b' font-family='Arial,sans-serif' font-size='26' text-anchor='middle'%3EPress Start camera or Live stream%3C/text%3E%3C/svg%3E";
  let currentPreviewMode = "idle";
  let overlaySettings = { ...DEFAULTS.overlay };
  let overlayPersistTimer = 0;
  let lastOverlaySource = 'stopped';
  let manualDriveActive = false;
  let failSafeStopSent = false;
  let previewMetricsTimer = 0;
  let previewMetricsInFlight = false;
  let lastPreviewSeq = null;
  let lastPreviewSeqAt = 0;
  let lastPreviewFps = null;
  let lastPreviewStats = null;
  let lastPreviewImageLoadAt = 0;

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
    if (filesNotice) {
      filesNotice.textContent = message;
      filesNotice.dataset.state = isOk(code) ? 'ok' : 'error';
    }
    setCode('files', code);
  }

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!Number.isFinite(value) || value <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let scaled = value;
    let unit = 0;
    while (scaled >= 1024 && unit < units.length - 1) {
      scaled /= 1024;
      unit += 1;
    }
    return `${scaled >= 10 || unit === 0 ? scaled.toFixed(0) : scaled.toFixed(1)} ${units[unit]}`;
  }

  function formatDateTime(value) {
    const parsed = Date.parse(String(value || ''));
    if (!Number.isFinite(parsed)) return 'n/a';
    return new Date(parsed).toLocaleString(undefined, { hour12: false });
  }

  function folderDisplayName(item, kind) {
    if (!item) return 'No folder selected';
    const prefix = kind === 'snapshot' ? 'Snapshot' : 'Recording';
    return `${prefix}: ${item.label || item.date || item.id || 'folder'}`;
  }

  function setFileActionButtons(item) {
    const hasItem = Boolean(item && item.id);
    const running = Boolean(item?.running);
    if (downloadZipButton) downloadZipButton.disabled = !hasItem;
    if (deleteFolderButton) {
      deleteFolderButton.disabled = !hasItem || running;
      deleteFolderButton.title = running
        ? 'Stop the active recording before deleting this folder.'
        : 'Delete the selected folder inside the PiSD recordings root.';
    }
  }

  function updateSelectedFileDetails() {
    const { kind, id, item } = selectedFileItem();
    const state = !item ? 'empty' : (item.running ? 'running' : 'ready');
    if (fileSummary) fileSummary.dataset.state = state;
    if (fileSummaryName) fileSummaryName.textContent = folderDisplayName(item, kind);
    if (fileSummaryFrames) fileSummaryFrames.textContent = item ? String(Number(item.frame_count || 0)) : '0';
    if (fileSummarySize) fileSummarySize.textContent = item ? formatBytes(item.bytes) : '0 B';
    if (fileSummaryModified) fileSummaryModified.textContent = item ? formatDateTime(item.modified_at_utc || item.started_at_utc) : 'n/a';
    if (fileSummaryId) fileSummaryId.textContent = item ? shortPath(id || item.id) : 'n/a';
    if (fileSummaryZip) fileSummaryZip.textContent = item ? shortPath(item.download_name || `PiSD_${kind}_${String(id || item.id).replaceAll('/', '_')}.zip`) : 'n/a';
    setFileActionButtons(item);
    return { kind, id, item };
  }

  function parseFrameAgeMs(lastFrameAt) {
    const parsed = Date.parse(String(lastFrameAt || ''));
    if (!Number.isFinite(parsed)) return null;
    return Math.max(0, Date.now() - parsed);
  }

  function formatFrameAge(ageMs) {
    if (!Number.isFinite(ageMs)) return 'n/a';
    if (ageMs < 1000) return `${Math.round(ageMs)} ms`;
    return `${(ageMs / 1000).toFixed(1)} s`;
  }

  function formatPreviewFps(value) {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n.toFixed(1) : 'n/a';
  }

  // 0.4.9: data-preview-state / data-preview-mode are the browser-side truth markers for preview health.
  function updatePreviewDebug({ mode = currentPreviewMode, cameraRunning = null, frameAgeMs = null, fps = null, loopActive = false, state = 'idle', frameSeq = null } = {}) {
    currentPreviewMode = mode;
    if (previewFrame) {
      previewFrame.dataset.previewMode = mode;
      previewFrame.dataset.previewState = state;
      if (frameSeq !== null && frameSeq !== undefined) previewFrame.dataset.previewSeq = String(frameSeq);
    }
    if (preview) preview.dataset.previewMode = mode;
    if (previewModeDebug) previewModeDebug.textContent = mode;
    if (previewCameraDebug) previewCameraDebug.textContent = cameraRunning === null ? 'unknown' : (cameraRunning ? 'yes' : 'no');
    if (previewAgeDebug) previewAgeDebug.textContent = formatFrameAge(frameAgeMs);
    if (previewFpsDebug) previewFpsDebug.textContent = formatPreviewFps(fps);
    if (previewLoopDebug) previewLoopDebug.textContent = loopActive ? 'on' : 'off';
  }

  function estimatePreviewFps(stats, nowMs = performance.now()) {
    const seq = Number(stats?.frame_seq);
    const serverMeasured = Number(stats?.measured_capture_fps);
    if (!Number.isFinite(seq)) return Number.isFinite(serverMeasured) ? serverMeasured : null;
    if (lastPreviewSeq === null) {
      lastPreviewSeq = seq;
      lastPreviewSeqAt = nowMs;
      return Number.isFinite(serverMeasured) ? serverMeasured : null;
    }
    const elapsed = Math.max(0.001, (nowMs - lastPreviewSeqAt) / 1000);
    const delta = seq - lastPreviewSeq;
    if (delta > 0) {
      lastPreviewFps = delta / elapsed;
      lastPreviewSeq = seq;
      lastPreviewSeqAt = nowMs;
    } else if (Number.isFinite(serverMeasured) && serverMeasured > 0 && lastPreviewFps === null) {
      lastPreviewFps = serverMeasured;
    }
    return lastPreviewFps;
  }

  function previewStateFromCamera(camera = {}, stats = camera) {
    const running = Boolean(camera.running ?? stats.running);
    const frameAgeMs = parseFrameAgeMs(stats.last_frame_at ?? camera.last_frame_at);
    if (currentPreviewMode === 'idle') return 'idle';
    if (!running) return 'camera-off';
    if (Number.isFinite(frameAgeMs) && frameAgeMs > PREVIEW_STALE_MS) return 'stale';
    return 'active';
  }

  function renderPreviewFromStatus(status) {
    const camera = status?.camera || {};
    const frameAgeMs = parseFrameAgeMs(camera.last_frame_at);
    const fps = Number(camera.measured_capture_fps ?? camera.fps);
    const state = previewStateFromCamera(camera);
    updatePreviewDebug({
      mode: currentPreviewMode,
      cameraRunning: Boolean(camera.running),
      frameAgeMs,
      fps: Number.isFinite(fps) ? fps : null,
      loopActive: Boolean(previewMetricsTimer),
      state,
      frameSeq: camera.frame_seq,
    });
  }

  function setPreviewIdle(message = 'Preview idle. Press Start camera or Live stream.') {
    currentPreviewMode = 'idle';
    if (preview) preview.src = PREVIEW_IDLE_SRC;
    stopPreviewMetricsLoop();
    updatePreviewDebug({ mode: 'idle', cameraRunning: null, frameAgeMs: null, fps: null, loopActive: false, state: 'idle' });
    setShortStatus(message, 'PISD-OK-000');
  }

  async function refreshPreviewMetrics() {
    if (previewMetricsInFlight) return;
    previewMetricsInFlight = true;
    try {
      const response = await fetch(`/api/camera/fps-stats?t=${Date.now()}`, { cache: 'no-store' });
      const payload = await response.json();
      const stats = payload.stats || {};
      lastPreviewStats = stats;
      const now = performance.now();
      const fps = estimatePreviewFps(stats, now);
      const frameAgeMs = parseFrameAgeMs(stats.last_frame_at);
      const cameraRunning = Boolean(payload.camera?.running ?? true);
      const state = previewStateFromCamera({ running: cameraRunning, last_frame_at: stats.last_frame_at }, stats);
      updatePreviewDebug({ mode: currentPreviewMode, cameraRunning, frameAgeMs, fps, loopActive: Boolean(previewMetricsTimer), state, frameSeq: stats.frame_seq });
      if (state === 'stale' && currentPreviewMode === 'live') {
        setShortStatus('Preview stale: camera is running but no fresh frame has arrived recently.', 'PISD-CAM-006');
      }
    } catch (_err) {
      updatePreviewDebug({ mode: currentPreviewMode, cameraRunning: null, frameAgeMs: null, fps: null, loopActive: Boolean(previewMetricsTimer), state: 'error' });
    } finally {
      previewMetricsInFlight = false;
    }
  }

  function startPreviewMetricsLoop() {
    if (previewMetricsTimer) return;
    refreshPreviewMetrics();
    previewMetricsTimer = window.setInterval(refreshPreviewMetrics, PREVIEW_METRICS_MS);
    updatePreviewDebug({ mode: currentPreviewMode, loopActive: true, state: previewFrame?.dataset.previewState || 'active' });
  }

  function stopPreviewMetricsLoop() {
    if (!previewMetricsTimer) return;
    window.clearInterval(previewMetricsTimer);
    previewMetricsTimer = 0;
  }

  function formatSigned(value) {
    const n = Number(value);
    const safe = Number.isFinite(n) ? Math.max(-1, Math.min(1, n)) : 0;
    return `${safe >= 0 ? '+' : ''}${safe.toFixed(2)}`;
  }


  function normaliseManualCommand(command = STOP_COMMAND) {
    const source = command && typeof command === 'object' ? command : STOP_COMMAND;
    return {
      steering: clamp(source.steering ?? 0, -1, 1, 0),
      throttle: clamp(source.throttle ?? 0, -1, 1, 0),
      steer_mix: clamp(source.steer_mix ?? 1.0, 0, 1, 1.0),
    };
  }

  function normaliseMotorOutput(output = STOP_OUTPUT) {
    const source = output && typeof output === 'object' ? output : STOP_OUTPUT;
    return {
      left: clamp(source.left ?? 0, -1, 1, 0),
      right: clamp(source.right ?? 0, -1, 1, 0),
    };
  }

  function driveStateIsMoving(command = lastPayload, output = lastMotorOutput) {
    const cmd = normaliseManualCommand(command);
    const out = normaliseMotorOutput(output);
    return Math.abs(cmd.steering) >= 0.02
      || Math.abs(cmd.throttle) >= 0.02
      || Math.abs(out.left) >= 0.02
      || Math.abs(out.right) >= 0.02;
  }

  function setDriveState(command = STOP_COMMAND, output = STOP_OUTPUT, sourceHint = 'manual intent') {
    lastPayload = normaliseManualCommand(command);
    lastMotorOutput = normaliseMotorOutput(output);
    manualDriveActive = driveStateIsMoving(lastPayload, lastMotorOutput);
    if (manualDriveActive) failSafeStopSent = false;
    renderMotorSignals(lastPayload, lastMotorOutput, sourceHint);
  }

  function setStoppedDriveState(sourceHint = 'stopped') {
    setKnob(0, 0);
    setDriveState(STOP_COMMAND, STOP_OUTPUT, sourceHint);
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
      curve_strength: clamp(source.curve_strength ?? DEFAULTS.overlay.curve_strength, 0.4, 5.0, DEFAULTS.overlay.curve_strength),
      opacity: clamp(source.opacity ?? DEFAULTS.overlay.opacity, 0.2, 1.0, DEFAULTS.overlay.opacity),
      path_width_scale: clamp(source.path_width_scale ?? DEFAULTS.overlay.path_width_scale, 0.3, 1.8, DEFAULTS.overlay.path_width_scale),
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

  const overlayGeometry = window.PiSDOverlayGeometry || null;

  function pointsToPath(points) {
    return overlayGeometry?.pointsToPath(points) || '';
  }

  function pointsToPolygonPath(leftPoints, rightPoints) {
    return overlayGeometry?.pointsToPolygonPath(leftPoints, rightPoints) || '';
  }

  function roadBoundaryPath(points) {
    return overlayGeometry?.roadBoundaryPath(points) || pointsToPath(points);
  }

  function roadGuideGeometry(throttle, steering) {
    if (!overlayGeometry?.roadGuideGeometry) {
      const movingReverse = Number(throttle) < -0.02;
      const fallbackLeft = [{ x: 32, y: 96 }, { x: 44, y: 31 }];
      const fallbackRight = [{ x: 68, y: 96 }, { x: 56, y: 31 }];
      const fallbackCenter = [{ x: 50, y: 96 }, { x: 50, y: 31 }];
      return {
        leftPath: roadBoundaryPath(fallbackLeft),
        rightPath: roadBoundaryPath(fallbackRight),
        centerPath: pointsToPath(fallbackCenter),
        surfacePath: pointsToPolygonPath(fallbackLeft, fallbackRight),
        start: fallbackCenter[0],
        end: fallbackCenter[fallbackCenter.length - 1],
        curve: 0,
        movingReverse,
        speed: Math.max(0, clamp(throttle, -1, 1, 0)),
      };
    }
    return overlayGeometry.roadGuideGeometry({
      throttle,
      steering,
      settings: overlaySettings,
      defaults: DEFAULTS.overlay,
    });
  }

  function drawIntendedPath(throttle, steering) {
    if (!overlayPath) return;
    const safeThrottle = clamp(throttle, -1, 1, 0);
    const safeSteering = clamp(steering, -1, 1, 0);
    const steeringAbs = Math.abs(safeSteering);
    const movingForward = safeThrottle >= 0.02;
    const movingReverse = safeThrottle < -0.02;
    const { leftPath, rightPath, centerPath, surfacePath, start, end, curve, speed } = roadGuideGeometry(safeThrottle, safeSteering);
    const calibratedOpacity = overlaySettings.opacity || DEFAULTS.overlay.opacity;
    const widthScale = overlaySettings.path_width_scale || 1.0;
    const opacity = movingReverse ? '0' : (movingForward || steeringAbs >= 0.02 ? String(calibratedOpacity) : String(Math.max(0.12, calibratedOpacity * 0.26)));

    if (overlaySurface) {
      overlaySurface.setAttribute('d', surfacePath);
      overlaySurface.style.opacity = movingReverse ? '0' : (movingForward ? String(Math.max(0.16, calibratedOpacity * 0.36)) : String(Math.max(0.04, calibratedOpacity * 0.10)));
    }
    if (overlayPathWide) {
      overlayPathWide.setAttribute('d', leftPath);
      overlayPathWide.style.opacity = opacity;
      overlayPathWide.style.strokeDasharray = 'none';
      overlayPathWide.style.strokeWidth = String(2.25 * widthScale);
    }
    if (overlayPathGuide) {
      overlayPathGuide.setAttribute('d', rightPath);
      overlayPathGuide.style.opacity = opacity;
      overlayPathGuide.style.strokeDasharray = 'none';
      overlayPathGuide.style.strokeWidth = String(2.25 * widthScale);
    }
    overlayPath.setAttribute('d', centerPath);
    overlayPath.style.opacity = movingReverse ? '0' : (movingForward ? String(Math.max(0.18, calibratedOpacity * 0.34)) : String(Math.max(0.08, calibratedOpacity * 0.16)));
    overlayPath.style.strokeDasharray = movingForward ? 'none' : '6 8';
    overlayPath.style.strokeWidth = String((1.15 + speed * 0.38) * widthScale);
    if (overlayStartPoint) {
      overlayStartPoint.setAttribute('cx', start.x.toFixed(2));
      overlayStartPoint.setAttribute('cy', start.y.toFixed(2));
      overlayStartPoint.style.opacity = movingReverse ? '0' : overlayPath.style.opacity;
    }
    if (overlayEndpoint) {
      overlayEndpoint.setAttribute('cx', end.x.toFixed(2));
      overlayEndpoint.setAttribute('cy', end.y.toFixed(2));
      overlayEndpoint.style.opacity = movingReverse ? '0' : overlayPath.style.opacity;
    }
    if (overlayCurveLabel) {
      if (movingReverse) {
        overlayCurveLabel.textContent = 'reverse · guide hidden';
      } else {
        const curveText = Math.abs(curve) < 0.08 ? 'trapezium' : `road curve ${Math.abs(curve).toFixed(2)}`;
        overlayCurveLabel.textContent = `${curveLabelText(safeThrottle, safeSteering)} · ${curveText}`;
      }
    }
    if (previewFrame) {
      previewFrame.dataset.overlayMotion = movingForward ? 'forward' : (movingReverse ? 'reverse' : 'stopped');
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
      command = STOP_COMMAND;
    }
    setDriveState(command, output, 'live status');
  }

  function renderMotorSignalsFromApiResponse(payload, fallbackCommand = lastPayload, sourceHint = 'live status') {
    const motor = payload?.motor || {};
    const command = motor.last_command || fallbackCommand || lastPayload;
    const output = {
      left: payload?.left ?? motor.last_left ?? lastMotorOutput.left,
      right: payload?.right ?? motor.last_right ?? lastMotorOutput.right,
    };
    setDriveState(command, output, sourceHint);
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
    const previous = fileSelect.value;
    fileSelect.innerHTML = '';
    if (!list.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = kind === 'snapshot' ? 'No snapshot folders' : 'No recording folders';
      fileSelect.appendChild(option);
      updateSelectedFileDetails();
      showFilesNotice(kind === 'snapshot' ? 'No snapshot folders found.' : 'No recording folders found.');
      return;
    }
    for (const item of list) {
      const option = document.createElement('option');
      option.value = item.id;
      const count = Number(item.frame_count || 0);
      const running = item.running ? ' ACTIVE' : '';
      option.textContent = `${item.date || ''}  ${item.label || item.id}  (${count} frames, ${formatBytes(item.bytes)})${running}`;
      fileSelect.appendChild(option);
    }
    if (previous && list.some(item => item.id === previous)) fileSelect.value = previous;
    const selected = updateSelectedFileDetails();
    showFilesNotice(`Selected ${kind}: ${selected.item?.id || selected.item?.label || 'folder'}`);
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
    const { kind, id, item } = updateSelectedFileDetails();
    if (!id || !item) {
      showFilesNotice('Select a folder before downloading.', 'PISD-REC-008');
      return;
    }
    const url = `/api/recording/download.zip?kind=${encodeURIComponent(kind)}&id=${encodeURIComponent(id)}`;
    const size = formatBytes(item.bytes);
    showFilesNotice(`Preparing ${kind} zip: ${id} (${size}). Browser download should start shortly.`, 'PISD-OK-000');
    window.location.assign(url);
  }

  async function deleteSelectedFolder() {
    const { kind, id, item } = updateSelectedFileDetails();
    if (!id || !item) {
      showFilesNotice('Select a folder before deleting.', 'PISD-REC-008');
      return;
    }
    if (item.running) {
      showFilesNotice('Stop the active recording before deleting its folder.', 'PISD-REC-009');
      return;
    }
    const label = item?.label || id;
    const details = `${Number(item.frame_count || 0)} frames, ${formatBytes(item.bytes)}, modified ${formatDateTime(item.modified_at_utc)}`;
    const ok = window.confirm(`Delete ${kind} folder?\n\n${label}\n${id}\n${details}\n\nOnly this selected PiSD recordings folder will be removed. This cannot be undone.`);
    if (!ok) return;
    try {
      if (deleteFolderButton) deleteFolderButton.disabled = true;
      showFilesNotice(`Deleting ${kind}: ${id}`, 'PISD-OK-000');
      const { payload } = await api('POST', '/api/recording/delete', { kind, id }, 'files');
      showFilesNotice(payload.ok ? `Deleted ${kind}: ${id}` : `Delete failed: ${payload.code} ${payload.message || ''}`.trim(), payload.code);
      await refreshRecordingItems();
    } catch (err) {
      showFilesNotice(`Delete failed: ${String(err)}`, 'PISD-REC-009');
      writeLog('recording delete failed', { ok: false, code: 'PISD-REC-009', message: String(err) });
    } finally {
      updateSelectedFileDetails();
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
    renderPreviewFromStatus(status);
    renderMotorSignalsFromStatus(status);
    setCode('status', status.code || 'PISD-OK-000');
    setGlobalCode(status.code || 'PISD-OK-000');
  }

  async function refreshStatus(userVisible = false) {
    try {
      const { payload } = await api('GET', '/api/status', undefined, 'status');
      renderStatus(payload);
      if (userVisible) {
        setShortStatus(`Status refreshed without touching camera preview or motor command: ${payload?.code || 'PISD-OK-000'}`, payload?.code || 'PISD-OK-000');
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
      safety_ack: Boolean(arm?.checked),
      enable_motor_output: Boolean(arm?.checked),
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
    setDriveState(payload, lastMotorOutput, 'manual intent');
    try {
      const result = await api('POST', '/api/control/manual', payload, 'drive');
      renderMotorSignalsFromApiResponse(result.payload, payload, 'live status');
    }
    catch (err) { writeLog('manual drag failed', { ok: false, code: 'PISD-API-002', message: String(err) }); }
  }

  async function stopAll(target = 'stop') {
    setStoppedDriveState('stopped');
    try {
      const { payload } = await api('POST', '/api/control/stop', {}, target);
      renderMotorSignalsFromApiResponse(payload, STOP_COMMAND, 'stopped');
      setShortStatus(`STOP motors sent: ${payload?.code || 'PISD-OK-000'} ${payload?.message || ''}`.trim(), payload?.code || 'PISD-OK-000');
      await refreshStatus();
    } catch (err) {
      writeLog('STOP failed', { ok: false, code: 'PISD-API-002', message: String(err) });
    }
  }

  function livePreview() {
    currentPreviewMode = 'live';
    lastPreviewSeq = null;
    lastPreviewSeqAt = 0;
    lastPreviewFps = null;
    if (preview) preview.src = `/video_feed?t=${Date.now()}`;
    updatePreviewDebug({ mode: 'live', cameraRunning: true, frameAgeMs: null, fps: null, loopActive: Boolean(previewMetricsTimer), state: 'active' });
    startPreviewMetricsLoop();
    setShortStatus('Live MJPEG preview selected. Metrics loop is guarded so only one status/FPS poller runs.', 'PISD-OK-000');
  }

  function snapshotView() {
    currentPreviewMode = 'snapshot';
    if (preview) preview.src = `/api/camera/frame.jpg?t=${Date.now()}`;
    updatePreviewDebug({ mode: 'snapshot', cameraRunning: true, frameAgeMs: null, fps: lastPreviewFps, loopActive: Boolean(previewMetricsTimer), state: 'loading' });
    startPreviewMetricsLoop();
    setShortStatus('Snapshot preview refreshed from the running camera service.', 'PISD-OK-000');
  }

  async function startCameraOnly() {
    try {
      const { payload } = await api('POST', '/api/camera/start', {}, 'camera');
      setShortStatus(`Camera start: ${payload?.code || 'PISD-OK-000'} ${payload?.message || ''}`.trim(), payload?.code || 'PISD-OK-000');
      snapshotView();
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


  function sendFailSafeStop(reason = 'pagehide') {
    if (!manualDriveActive && !dragging && !driveStateIsMoving(lastPayload, lastMotorOutput)) return;
    if (failSafeStopSent) return;
    failSafeStopSent = true;
    dragging = false;
    setStoppedDriveState('stopped');
    const body = JSON.stringify({ reason, source: 'manual-drive-failsafe' });
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: 'application/json' });
        navigator.sendBeacon('/api/control/stop', blob);
        return;
      }
    } catch (_err) {}
    try {
      fetch('/api/control/stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {});
    } catch (_err) {}
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
    fileSelect?.addEventListener('change', () => {
      const selected = updateSelectedFileDetails();
      if (selected.item) showFilesNotice(`Selected ${selected.kind}: ${selected.id}`);
    });
    toggleLog?.addEventListener('click', () => {
      const hidden = logPanel?.hasAttribute('hidden');
      if (hidden) logPanel.removeAttribute('hidden'); else logPanel?.setAttribute('hidden', '');
      toggleLog.textContent = hidden ? 'Hide action log' : 'Show action log';
    });
    arm?.addEventListener('change', () => { updateLock(); if (!arm?.checked) stopAll('drive'); });
    preview?.addEventListener('load', () => {
      lastPreviewImageLoadAt = Date.now();
      if (currentPreviewMode !== 'idle') updatePreviewDebug({ mode: currentPreviewMode, cameraRunning: true, frameAgeMs: 0, fps: lastPreviewFps, loopActive: Boolean(previewMetricsTimer), state: 'active' });
    });
    preview?.addEventListener('error', () => {
      if (currentPreviewMode !== 'idle') updatePreviewDebug({ mode: currentPreviewMode, cameraRunning: null, frameAgeMs: null, fps: null, loopActive: Boolean(previewMetricsTimer), state: 'error' });
    });
    window.addEventListener('pagehide', () => { stopPreviewMetricsLoop(); sendFailSafeStop('pagehide'); });
    window.addEventListener('beforeunload', () => sendFailSafeStop('beforeunload'));
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') { stopPreviewMetricsLoop(); sendFailSafeStop('visibility-hidden'); } else if (currentPreviewMode === 'live' || currentPreviewMode === 'snapshot') { startPreviewMetricsLoop(); } });
    speed?.addEventListener('input', () => { updateSliderLabels(); persistManualSettings(); setKnob(lastPayload.steering / Math.max(0.001, currentSteer()), -lastPayload.throttle / Math.max(0.001, currentSpeed())); });
    steer?.addEventListener('input', () => { updateSliderLabels(); persistManualSettings(); setKnob(lastPayload.steering / Math.max(0.001, currentSteer()), -lastPayload.throttle / Math.max(0.001, currentSpeed())); });
    bindPad();
  }

  setPreviewIdle('Preview idle. Press Start camera or Live stream.');
  setKnob(0, 0);
  setDriveState(STOP_COMMAND, STOP_OUTPUT, 'stopped');
  renderStatus(initialStatus);
  bind();
  applyOverlayCalibration(overlaySettings, false);
  updateDriveOverlay(lastPayload, lastMotorOutput, 'stopped');
  updateLock();
  loadSettings();
  refreshRecordingItems();
})();
