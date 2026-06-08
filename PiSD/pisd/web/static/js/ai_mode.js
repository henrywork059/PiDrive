(() => {
  const initial = JSON.parse(document.getElementById('aiModeInitialStatus')?.textContent || '{}');
  const els = {};
  const ids = [
    'aiGlobalCode', 'aiRunMode', 'aiModelReady', 'aiPreviewFrame', 'aiPreviewImage', 'aiPreviewCaption', 'aiSaveSnapshot', 'aiLive', 'aiRecordToggle', 'aiRecordingState', 'aiStopCamera',
    'aiOverlayToggle', 'aiOverlayMode', 'aiOverlayCurveLabel', 'aiOverlayCar', 'aiOverlaySurface', 'aiOverlayPathWide', 'aiOverlayPathGuide', 'aiOverlayPath',
    'aiOverlayEndpoint', 'aiOverlayStartPoint', 'aiOverlayThrottleFill', 'aiOverlaySteeringFill', 'aiOverlayThrottleValue', 'aiOverlaySteeringValue',
    'aiOverlayRawSteering', 'aiOverlayRawThrottle', 'aiOverlayLeftValue', 'aiOverlayRightValue',
    'aiRefreshModels', 'aiModelSelect', 'aiLoadModel', 'aiPredictOnce', 'aiDeleteModel', 'aiModelUploadFile', 'aiUploadModel', 'aiUploadHint', 'aiSelectedModel', 'aiBackend', 'aiInputShape', 'aiOutputNames', 'aiPiTrainerCompatible', 'aiRuntimeSupport', 'aiRuntimeHelp', 'aiRuntimeHelpCommands', 'aiLoadError', 'aiModelsDir',
    'aiSafetyAck', 'aiEnableMotor', 'aiOutputMode', 'aiMaxThrottle', 'aiMaxThrottleOut', 'aiMaxSteering', 'aiMaxSteeringOut',
    'aiFixedThrottle', 'aiFixedThrottleOut', 'aiUpdateHz', 'aiUpdateHzOut', 'aiSteerSmooth', 'aiSteerSmoothOut', 'aiThrottleSmooth',
    'aiThrottleSmoothOut', 'aiSaveConfig', 'aiLimiterTab', 'aiCorrectionTab', 'aiManualDriveTab', 'aiLimiterPane', 'aiCorrectionPane', 'aiManualDrivePane', 'aiManualMix', 'aiManualMixOut',
    'aiCorrectionPad', 'aiCorrectionKnob', 'aiCorrectionStatus', 'aiManualSteeringOut', 'aiManualThrottleOut', 'aiManualMixReadout',
    'aiManualDriveSpeed', 'aiManualDriveSpeedOut', 'aiManualDrivePad', 'aiManualDriveKnob', 'aiManualDriveStatus', 'aiManualDriveSteeringOut', 'aiManualDriveThrottleOut', 'aiManualDriveStop',
    'aiStartPreview', 'aiStartDrive', 'aiStop', 'aiStopAll', 'aiRawSteering', 'aiRawThrottle', 'aiMixedSteering', 'aiMixedThrottle',
    'aiSafeSteering', 'aiSafeThrottle', 'aiManualCorrectionState', 'aiLeftMotor', 'aiRightMotor', 'aiInferenceMs', 'aiLoopHz', 'aiDriveOutputState', 'aiFrameSeq', 'aiRefreshStatus', 'aiLog'
  ];
  ids.forEach((id) => { els[id] = document.getElementById(id); });

  const IDLE_PREVIEW_SRC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'%3E%3Crect width='1280' height='720' fill='%23020617'/%3E%3Ctext x='640' y='340' fill='%2394a3b8' font-family='Arial,sans-serif' font-size='42' text-anchor='middle'%3EAI preview idle%3C/text%3E%3Ctext x='640' y='398' fill='%2364748b' font-family='Arial,sans-serif' font-size='26' text-anchor='middle'%3EStart live, then run AI preview%3C/text%3E%3C/svg%3E";
  const AI_OVERLAY_SETTINGS = {
    path_length_scale: 1.0,
    // PiSD_0_5_9: mirror Manual Drive's road-edge overlay guide.
    curve_strength: 3.35,
    opacity: 0.94,
    path_width_scale: 0.34,
    turn_rate_visual_scale: 2.2,
  };
  const DEFAULT_MOTOR_SETTINGS = {
    steering_mode: 'turn_rate',
    steer_mix: 1.0,
    min_inside_speed: 0.0,
    allow_pivot_turn: false,
  };

  let statusTimer = null;
  let aiRunning = false;
  let recordingRunning = Boolean(initial.recording?.running);
  let overlayEnabled = true;
  let lastAIStatus = initial.ai_mode || {};
  let aiMotorEnableInitialised = false;
  let latestMotorSettings = { ...DEFAULT_MOTOR_SETTINGS };
  let outputPanelMode = Boolean((lastAIStatus.settings || {}).manual_correction_enabled) ? 'correction' : 'limiter';
  let correctionPanelActive = outputPanelMode === 'correction';
  let correctionDragging = false;
  let correctionSteering = 0;
  let correctionThrottle = 0;
  let correctionLastSentAt = 0;
  let correctionKeyboardSteering = 0;
  let correctionKeyboardThrottle = 0;
  let correctionKeyboardLeftHeld = false;
  let correctionKeyboardRightHeld = false;
  let correctionKeyboardLoopHandle = 0;
  let correctionKeyboardLastFrameAt = 0;
  let manualDriveDragging = false;
  let manualDriveSteering = 0;
  let manualDriveThrottle = 0;
  let manualDriveLastSentAt = 0;
  let manualDriveKeyboardSteering = 0;
  let manualDriveKeyboardThrottle = 0;
  let manualDriveKeyboardLeftHeld = false;
  let manualDriveKeyboardRightHeld = false;
  let manualDriveKeyboardLoopHandle = 0;
  let manualDriveKeyboardLastFrameAt = 0;
  const CORRECTION_SEND_INTERVAL_MS = 90;
  const KEYBOARD_THROTTLE_STEP = 0.05;
  const KEYBOARD_STEERING_FULL_SCALE_MS = 800;

  function clamp(value, min = -1, max = 1, fallback = 0) {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  }

  function normaliseMotorOverlaySettings(raw = {}) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const mode = String(source.steering_mode || DEFAULT_MOTOR_SETTINGS.steering_mode).trim().toLowerCase();
    const allowPivot = typeof source.allow_pivot_turn === 'string'
      ? ['true', '1', 'yes', 'on'].includes(source.allow_pivot_turn.trim().toLowerCase())
      : Boolean(source.allow_pivot_turn ?? DEFAULT_MOTOR_SETTINGS.allow_pivot_turn);
    return {
      steering_mode: mode === 'arcade_mix' ? 'arcade_mix' : 'turn_rate',
      steer_mix: clamp(source.steer_mix, 0, 2, DEFAULT_MOTOR_SETTINGS.steer_mix),
      min_inside_speed: clamp(source.min_inside_speed, 0, 0.99, DEFAULT_MOTOR_SETTINGS.min_inside_speed),
      allow_pivot_turn: allowPivot,
    };
  }

  function updateOverlayMotorSettings(motor = {}) {
    latestMotorSettings = normaliseMotorOverlaySettings({ ...latestMotorSettings, ...(motor || {}) });
  }

  function fmt(value, digits = 2) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits) : '-';
  }

  function formatSigned(value, digits = 2) {
    const n = clamp(value, -999, 999, 0);
    return `${n >= 0 ? '+' : ''}${n.toFixed(digits)}`;
  }

  function log(message, payload) {
    const time = new Date().toLocaleTimeString();
    const body = payload ? `${message}\n${JSON.stringify(payload, null, 2)}` : message;
    if (els.aiLog) els.aiLog.textContent = `[${time}] ${body}`;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      method: options.method || 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: 'no-store',
      keepalive: Boolean(options.keepalive),
    });
    const data = await response.json().catch(() => ({ ok: false, message: `HTTP ${response.status}` }));
    if (!response.ok || data.ok === false) {
      const message = data.message || `Request failed: ${path}`;
      throw Object.assign(new Error(message), { payload: data, status: response.status });
    }
    return data;
  }

  function collectConfig() {
    return {
      output_mode: els.aiOutputMode?.value || 'steering_and_throttle',
      max_throttle: Number(els.aiMaxThrottle?.value || 0.22),
      max_steering: Number(els.aiMaxSteering?.value || 0.70),
      fixed_throttle: Number(els.aiFixedThrottle?.value || 0.16),
      update_hz: Number(els.aiUpdateHz?.value || 12),
      steering_smoothing: Number(els.aiSteerSmooth?.value || 0.35),
      throttle_smoothing: Number(els.aiThrottleSmooth?.value || 0.25),
      manual_correction_enabled: outputPanelMode === 'correction',
      manual_mix_percent: Number(els.aiManualMix?.value || 50),
      manual_correction_timeout_s: 0.75,
    };
  }

  function setRange(id, outputId, value, digits = 2) {
    if (els[id]) els[id].value = String(value);
    if (els[outputId]) els[outputId].textContent = fmt(value, digits);
  }

  function setPercentRange(id, outputId, value) {
    const percent = clamp(value, 0, 100, 50);
    if (els[id]) els[id].value = String(percent);
    if (els[outputId]) els[outputId].textContent = `${Math.round(percent)}%`;
    if (els.aiManualMixReadout) els.aiManualMixReadout.textContent = `${Math.round(percent)}%`;
  }

  function renderConfig(config = {}) {
    if (els.aiOutputMode) els.aiOutputMode.value = config.output_mode || 'steering_and_throttle';
    // PiSD_0_5_12: never restore motor output enable from saved config; it is session-only.
    // Only clear it during initial render so Save/Refresh does not unexpectedly uncheck
    // the live checkbox immediately before Start AI Drive reads it.
    if (els.aiEnableMotor && !aiMotorEnableInitialised) {
      els.aiEnableMotor.checked = false;
      aiMotorEnableInitialised = true;
    }
    setRange('aiMaxThrottle', 'aiMaxThrottleOut', config.max_throttle ?? 0.22);
    setRange('aiMaxSteering', 'aiMaxSteeringOut', config.max_steering ?? 0.70);
    setRange('aiFixedThrottle', 'aiFixedThrottleOut', config.fixed_throttle ?? 0.16);
    setRange('aiUpdateHz', 'aiUpdateHzOut', config.update_hz ?? 12, 0);
    setRange('aiSteerSmooth', 'aiSteerSmoothOut', config.steering_smoothing ?? 0.35);
    setRange('aiThrottleSmooth', 'aiThrottleSmoothOut', config.throttle_smoothing ?? 0.25);
    setPercentRange('aiManualMix', 'aiManualMixOut', config.manual_mix_percent ?? 50);
    if (outputPanelMode !== 'manual') {
      setOutputPanel(Boolean(config.manual_correction_enabled) ? 'correction' : 'limiter', false);
    }
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
    const direction = throttle < -0.02 ? 'AI REV' : throttle > 0.02 ? 'AI FWD' : 'AI TURN';
    if (steeringAbs < 0.08) return direction;
    return `${direction} ${steering < 0 ? 'LEFT' : 'RIGHT'}`;
  }

  function curveLabelText(throttle, steering, ai = lastAIStatus) {
    const throttleAbs = Math.abs(throttle);
    const steeringAbs = Math.abs(steering);
    const source = ai.running ? (ai.mode === 'drive' ? 'drive' : 'preview') : ai.model_ready ? 'ready' : 'model not loaded';
    if (throttleAbs < 0.02 && steeringAbs < 0.02) return `${source} · hold`;
    if (steeringAbs < 0.06) return `${source} · straight`;
    const tightness = steeringAbs > 0.72 ? 'tight' : steeringAbs > 0.38 ? 'medium' : 'gentle';
    const turn = steering < 0 ? 'left' : 'right';
    return `${source} · ${tightness} ${turn}`;
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
      settings: AI_OVERLAY_SETTINGS,
      defaults: AI_OVERLAY_SETTINGS,
      motorSettings: latestMotorSettings,
    });
  }

  function drawAIPath(throttle, steering) {
    if (!els.aiOverlayPath) return;
    const safeThrottle = clamp(throttle, -1, 1, 0);
    const safeSteering = clamp(steering, -1, 1, 0);
    const steeringAbs = Math.abs(safeSteering);
    const movingForward = safeThrottle >= 0.02;
    const movingReverse = safeThrottle < -0.02;
    const { leftPath, rightPath, centerPath, surfacePath, start, end, curve, speed, turnIntent, steeringMode } = roadGuideGeometry(safeThrottle, safeSteering);
    const opacity = movingReverse ? '0' : (movingForward || steeringAbs >= 0.02 ? String(AI_OVERLAY_SETTINGS.opacity) : String(Math.max(0.12, AI_OVERLAY_SETTINGS.opacity * 0.26)));
    const widthScale = AI_OVERLAY_SETTINGS.path_width_scale;
    if (els.aiOverlaySurface) {
      els.aiOverlaySurface.setAttribute('d', surfacePath);
      els.aiOverlaySurface.style.opacity = movingReverse ? '0' : (movingForward ? String(Math.max(0.16, AI_OVERLAY_SETTINGS.opacity * 0.36)) : String(Math.max(0.04, AI_OVERLAY_SETTINGS.opacity * 0.10)));
    }
    if (els.aiOverlayPathWide) {
      els.aiOverlayPathWide.setAttribute('d', leftPath);
      els.aiOverlayPathWide.style.opacity = opacity;
      els.aiOverlayPathWide.style.strokeDasharray = 'none';
      els.aiOverlayPathWide.style.strokeWidth = String(2.25 * widthScale);
    }
    if (els.aiOverlayPathGuide) {
      els.aiOverlayPathGuide.setAttribute('d', rightPath);
      els.aiOverlayPathGuide.style.opacity = opacity;
      els.aiOverlayPathGuide.style.strokeDasharray = 'none';
      els.aiOverlayPathGuide.style.strokeWidth = String(2.25 * widthScale);
    }
    if (els.aiOverlayPath) {
      els.aiOverlayPath.setAttribute('d', centerPath);
      els.aiOverlayPath.style.opacity = movingReverse ? '0' : (movingForward ? String(Math.max(0.18, AI_OVERLAY_SETTINGS.opacity * 0.34)) : String(Math.max(0.08, AI_OVERLAY_SETTINGS.opacity * 0.16)));
      els.aiOverlayPath.style.strokeDasharray = movingForward ? 'none' : '6 8';
      els.aiOverlayPath.style.strokeWidth = String((1.15 + speed * 0.38) * widthScale);
    }
    if (els.aiOverlayStartPoint) {
      els.aiOverlayStartPoint.setAttribute('cx', start.x.toFixed(2));
      els.aiOverlayStartPoint.setAttribute('cy', start.y.toFixed(2));
      els.aiOverlayStartPoint.style.opacity = movingReverse ? '0' : (els.aiOverlayPath?.style.opacity || opacity);
    }
    if (els.aiOverlayEndpoint) {
      els.aiOverlayEndpoint.setAttribute('cx', end.x.toFixed(2));
      els.aiOverlayEndpoint.setAttribute('cy', end.y.toFixed(2));
      els.aiOverlayEndpoint.style.opacity = movingReverse ? '0' : (els.aiOverlayPath?.style.opacity || opacity);
    }
    if (els.aiOverlayCurveLabel) {
      if (movingReverse) {
        els.aiOverlayCurveLabel.textContent = `${curveLabelText(safeThrottle, safeSteering)} · reverse guide hidden`;
      } else {
        const curveText = Math.abs(curve) < 0.08 ? 'trapezium' : `road curve ${Math.abs(curve).toFixed(2)}`;
        const modeText = steeringMode === 'arcade_mix' ? 'arcade overlay' : `turn ${Math.abs(Number(turnIntent || 0)).toFixed(2)}`;
        els.aiOverlayCurveLabel.textContent = `${curveLabelText(safeThrottle, safeSteering)} · ${modeText} · ${curveText}`;
      }
    }
    if (els.aiPreviewFrame) {
      els.aiPreviewFrame.dataset.overlayMotion = movingForward ? 'forward' : (movingReverse ? 'reverse' : 'stopped');
    }
  }

  function setOverlayEnabled(enabled) {
    overlayEnabled = Boolean(enabled);
    if (els.aiPreviewFrame) els.aiPreviewFrame.classList.toggle('mdrv-overlay-enabled', overlayEnabled);
    if (els.aiOverlayToggle) {
      els.aiOverlayToggle.textContent = overlayEnabled ? 'Overlay: On' : 'Overlay: Off';
      els.aiOverlayToggle.setAttribute('aria-pressed', overlayEnabled ? 'true' : 'false');
      els.aiOverlayToggle.dataset.state = overlayEnabled ? 'on' : 'off';
    }
  }

  function updateAIOverlay(ai = lastAIStatus) {
    const raw = ai.last_raw_prediction || {};
    const mixed = ai.last_corrected_command || ai.last_mixed_command || {};
    const safe = ai.last_safe_command || {};
    const manual = ai.manual_correction || {};
    const motor = ai.last_motor_output || {};
    const steering = clamp(safe.steering ?? 0, -1, 1, 0);
    const throttle = clamp(safe.throttle ?? 0, -1, 1, 0);
    const rawSteering = clamp(raw.steering ?? 0, -1, 1, 0);
    const rawThrottle = clamp(raw.throttle ?? 0, -1, 1, 0);
    const left = clamp(motor.left_intended ?? motor.intended_left ?? motor.last_intended_left ?? motor.left ?? 0, -1, 1, 0);
    const right = clamp(motor.right_intended ?? motor.intended_right ?? motor.last_intended_right ?? motor.right ?? 0, -1, 1, 0);
    const source = ai.running ? (ai.mode === 'drive' ? 'ai-drive' : 'ai-preview') : (ai.model_ready ? 'ai-ready' : 'ai-stopped');
    if (els.aiPreviewFrame) els.aiPreviewFrame.dataset.overlaySource = source;
    if (els.aiOverlayMode) els.aiOverlayMode.textContent = driveModeText(throttle, steering);
    if (els.aiOverlayThrottleValue) els.aiOverlayThrottleValue.textContent = formatSigned(throttle);
    if (els.aiOverlaySteeringValue) els.aiOverlaySteeringValue.textContent = formatSigned(steering);
    if (els.aiOverlayRawSteering) els.aiOverlayRawSteering.textContent = formatSigned(rawSteering);
    if (els.aiOverlayRawThrottle) els.aiOverlayRawThrottle.textContent = formatSigned(rawThrottle);
    if (els.aiOverlayLeftValue) els.aiOverlayLeftValue.textContent = formatSigned(left);
    if (els.aiOverlayRightValue) els.aiOverlayRightValue.textContent = formatSigned(right);
    setSignedFill(els.aiOverlayThrottleFill, throttle);
    setSignedFill(els.aiOverlaySteeringFill, steering);
    drawAIPath(throttle, steering);
  }

  function renderAI(ai = {}) {
    lastAIStatus = ai || {};
    aiRunning = Boolean(ai.running);
    const raw = ai.last_raw_prediction || {};
    const mixed = ai.last_corrected_command || ai.last_mixed_command || {};
    const safe = ai.last_safe_command || {};
    const manual = ai.manual_correction || {};
    const motor = ai.last_motor_output || {};
    if (els.aiRunMode) els.aiRunMode.textContent = ai.mode || 'idle';
    if (els.aiModelReady) els.aiModelReady.textContent = ai.model_ready ? 'ready' : (ai.model_loaded ? 'loaded' : 'not loaded');
    if (els.aiSelectedModel) els.aiSelectedModel.textContent = ai.model_id || 'none';
    if (els.aiBackend) {
      const backend = ai.backend || 'none';
      const detail = ai.backend_detail || '';
      els.aiBackend.textContent = detail && detail !== backend ? `${backend} (${detail})` : backend;
    }
    const runtime = ai.runtime_support || {};
    if (els.aiRuntimeSupport) {
      const bits = [];
      bits.push(runtime.tflite ? 'TFLite OK' : 'TFLite missing');
      bits.push(runtime.keras ? 'Keras OK' : 'Keras missing');
      els.aiRuntimeSupport.textContent = bits.join(' / ');
      els.aiRuntimeSupport.dataset.state = runtime.tflite || runtime.keras ? 'ok' : 'missing';
    }
    if (els.aiRuntimeHelp) {
      const showHelp = !runtime.tflite;
      els.aiRuntimeHelp.hidden = !showHelp;
      if (els.aiRuntimeHelpCommands) {
        const commands = Array.isArray(runtime.install_commands) && runtime.install_commands.length
          ? runtime.install_commands
          : ['cd ~/PiDrive/PiSD', 'python3 scripts/install_ai_runtime.py --runtime tflite-runtime', 'python3 scripts/check_ai_runtime.py'];
        els.aiRuntimeHelpCommands.textContent = commands.join('\n');
      }
    }
    if (els.aiLoadError) {
      const message = ai.last_error || '';
      els.aiLoadError.textContent = message || 'none';
      els.aiLoadError.dataset.state = message ? 'error' : 'ok';
    }
    if (els.aiModelsDir) els.aiModelsDir.textContent = ai.models_dir || 'models';
    const input = ai.input_size || {};
    if (els.aiInputShape) els.aiInputShape.textContent = input.width ? `${input.width} × ${input.height}` : '-';
    if (els.aiOutputNames) els.aiOutputNames.textContent = (ai.output_names || []).length ? (ai.output_names || []).join(', ') : '-';
    if (els.aiPiTrainerCompatible) els.aiPiTrainerCompatible.textContent = ai.piTrainer_export_compatible ? 'yes' : (ai.model_ready ? 'unknown' : 'not loaded');
    if (els.aiRawSteering) els.aiRawSteering.textContent = fmt(raw.steering);
    if (els.aiRawThrottle) els.aiRawThrottle.textContent = fmt(raw.throttle);
    if (els.aiMixedSteering) els.aiMixedSteering.textContent = fmt(mixed.steering ?? raw.steering);
    if (els.aiMixedThrottle) els.aiMixedThrottle.textContent = fmt(mixed.throttle ?? raw.throttle);
    if (els.aiManualCorrectionState) {
      const manualCorrectionPercent = Math.round(clamp(manual.mix_percent ?? (mixed.manual_weight ?? 0) * 100, 0, 100, 0));
      els.aiManualCorrectionState.textContent = manual.enabled
        ? `${manual.active ? 'active' : 'ready'} · ${manualCorrectionPercent}%`
        : 'off';
    }
    if (els.aiSafeSteering) els.aiSafeSteering.textContent = fmt(safe.steering);
    if (els.aiSafeThrottle) els.aiSafeThrottle.textContent = fmt(safe.throttle);
    if (els.aiReverseSteeringPolicy) {
      const safety = ai.safety_layer || {};
      els.aiReverseSteeringPolicy.textContent = safety.reverse_steering_policy === 'same_sign' ? 'same sign' : (safety.reverse_steering_policy || 'same sign');
    }
    const motorLeftIntent = motor.left_intended ?? motor.intended_left ?? motor.last_intended_left ?? motor.left;
    const motorRightIntent = motor.right_intended ?? motor.intended_right ?? motor.last_intended_right ?? motor.right;
    if (els.aiLeftMotor) els.aiLeftMotor.textContent = fmt(motorLeftIntent);
    if (els.aiRightMotor) els.aiRightMotor.textContent = fmt(motorRightIntent);
    if (els.aiInferenceMs) els.aiInferenceMs.textContent = `${fmt(ai.last_inference_ms, 1)} ms`;
    if (els.aiLoopHz) els.aiLoopHz.textContent = `${fmt(ai.loop_hz, 1)} Hz`;
    if (els.aiDriveOutputState) els.aiDriveOutputState.textContent = ai.drive_output_enabled ? 'armed' : 'off';
    if (els.aiFrameSeq) els.aiFrameSeq.textContent = String(ai.last_frame_seq ?? 0);
    if (ai.settings) renderConfig(ai.settings);
    updateAIOverlay(ai);
  }

  function renderRecording(recording = {}) {
    recordingRunning = Boolean(recording.running);
    if (els.aiRecordingState) {
      els.aiRecordingState.dataset.recording = recordingRunning ? 'on' : 'off';
      els.aiRecordingState.textContent = recordingRunning ? `REC on ${Number(recording.frame_count || 0)} frames` : 'REC off';
    }
    if (els.aiRecordToggle) {
      els.aiRecordToggle.textContent = recordingRunning ? 'Stop rec' : 'Record';
      els.aiRecordToggle.classList.toggle('mdrv-recording-on', recordingRunning);
    }
  }

  async function refreshStatus() {
    try {
      const data = await api('/api/ai/status');
      updateOverlayMotorSettings(data.motor || {});
      renderAI(data.ai || {});
      renderRecording(data.recording || {});
      if (els.aiGlobalCode) els.aiGlobalCode.textContent = data.code || 'PISD-OK-000';
      return data;
    } catch (err) {
      log(err.message, err.payload || {});
      return null;
    }
  }

  async function refreshModels() {
    try {
      const data = await api('/api/ai/models');
      const models = data.models || [];
      if (els.aiModelSelect) {
        els.aiModelSelect.innerHTML = '';
        if (!models.length) {
          const opt = document.createElement('option');
          opt.value = '';
          opt.textContent = 'No model files found in PiSD/models';
          els.aiModelSelect.appendChild(opt);
        } else {
          models.forEach((model) => {
            const opt = document.createElement('option');
            opt.value = model.id;
            opt.textContent = `${model.id} (${Math.round((model.bytes || 0) / 1024)} KB)`;
            els.aiModelSelect.appendChild(opt);
          });
        }
      }
      log('Model list refreshed.', { count: models.length, supported_extensions: data.supported_extensions });
      return models;
    } catch (err) {
      log(err.message, err.payload || {});
      return [];
    }
  }

  function enforceFullScaleThrottleRanges() {
    ['aiMaxThrottle', 'aiFixedThrottle'].forEach((id) => {
      if (!els[id]) return;
      els[id].min = '0';
      els[id].max = '1.0';
      els[id].step = '0.01';
    });
    if (els.aiUpdateHz) {
      els.aiUpdateHz.min = '1';
      els.aiUpdateHz.max = '60';
      els.aiUpdateHz.step = '1';
    }
  }

  function updateCorrectionStatus(message, state = 'ready') {
    if (!els.aiCorrectionStatus) return;
    els.aiCorrectionStatus.textContent = message;
    els.aiCorrectionStatus.dataset.state = state;
  }

  function updateCorrectionReadout() {
    if (els.aiManualSteeringOut) els.aiManualSteeringOut.textContent = formatSigned(correctionSteering);
    if (els.aiManualThrottleOut) els.aiManualThrottleOut.textContent = formatSigned(correctionThrottle);
    setPercentRange('aiManualMix', 'aiManualMixOut', els.aiManualMix?.value || 50);
  }

  function setCorrectionKnob(steering, throttle) {
    correctionSteering = clamp(steering, -1, 1, 0);
    correctionThrottle = clamp(throttle, -1, 1, 0);
    if (els.aiCorrectionKnob) {
      els.aiCorrectionKnob.style.setProperty('--knob-left', `${50 + correctionSteering * 50}%`);
      els.aiCorrectionKnob.style.setProperty('--knob-top', `${50 - correctionThrottle * 50}%`);
    }
    updateCorrectionReadout();
    return { steering: correctionSteering, throttle: correctionThrottle };
  }

  function manualDrivePanelActive() {
    return outputPanelMode === 'manual';
  }

  function setPanelTab(tab, active) {
    if (!tab) return;
    tab.classList.toggle('is-active', Boolean(active));
    tab.setAttribute('aria-selected', String(Boolean(active)));
  }

  function resetCorrectionKeyboardState() {
    stopCorrectionKeyboardLoop();
    correctionKeyboardSteering = 0;
    correctionKeyboardThrottle = 0;
    correctionKeyboardLeftHeld = false;
    correctionKeyboardRightHeld = false;
    setCorrectionKnob(0, 0);
  }

  function setOutputPanel(mode = 'limiter', persist = false) {
    const nextMode = ['limiter', 'correction', 'manual'].includes(mode) ? mode : 'limiter';
    const wasCorrection = correctionPanelActive;
    const wasManual = manualDrivePanelActive();
    outputPanelMode = nextMode;
    correctionPanelActive = outputPanelMode === 'correction';
    const manualActive = manualDrivePanelActive();

    if (els.aiLimiterPane) els.aiLimiterPane.hidden = outputPanelMode !== 'limiter';
    if (els.aiCorrectionPane) els.aiCorrectionPane.hidden = outputPanelMode !== 'correction';
    if (els.aiManualDrivePane) els.aiManualDrivePane.hidden = !manualActive;
    setPanelTab(els.aiLimiterTab, outputPanelMode === 'limiter');
    setPanelTab(els.aiCorrectionTab, outputPanelMode === 'correction');
    setPanelTab(els.aiManualDriveTab, manualActive);

    if (!correctionPanelActive) {
      resetCorrectionKeyboardState();
      if (wasCorrection || persist) sendManualCorrection(true, 'ai-correction-disabled', true);
      updateCorrectionStatus(manualActive ? 'Correction disabled while full manual pad is active.' : 'Correction disabled. AI output uses the limiter only.', 'ready');
    } else {
      updateCorrectionStatus('Correction active. Drag pad / arrow keys are added to AI output by the Correction %.', 'active');
    }

    if (wasManual && !manualActive) stopFullManualDrive('ai-manual-pane-exit');
    if (manualActive) updateManualDriveStatus('Manual pad active. Direct manual commands will stop AI drive control.', 'active');

    if (persist) saveConfig();
  }

  function setCorrectionPanel(active, persist = false) {
    setOutputPanel(active ? 'correction' : 'limiter', persist);
  }

  function pointerToCorrection(event) {
    const rect = els.aiCorrectionPad.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / Math.max(1, rect.width) - 0.5) * 2;
    const y = ((event.clientY - rect.top) / Math.max(1, rect.height) - 0.5) * 2;
    return setCorrectionKnob(x, -y);
  }

  function manualDriveSpeedLimit() {
    return clamp(els.aiManualDriveSpeed?.value || 0.18, 0, 1, 0.18);
  }

  function updateManualDriveStatus(message, state = 'ready') {
    if (!els.aiManualDriveStatus) return;
    els.aiManualDriveStatus.textContent = message;
    els.aiManualDriveStatus.dataset.state = state;
  }

  function updateManualDriveReadout() {
    if (els.aiManualDriveSpeedOut) els.aiManualDriveSpeedOut.textContent = fmt(manualDriveSpeedLimit(), 2);
    if (els.aiManualDriveSteeringOut) els.aiManualDriveSteeringOut.textContent = formatSigned(manualDriveSteering);
    if (els.aiManualDriveThrottleOut) els.aiManualDriveThrottleOut.textContent = formatSigned(manualDriveThrottle);
  }

  function setManualDriveKnob(steering, throttle) {
    const speedLimit = manualDriveSpeedLimit();
    const knobScale = Math.max(0.001, speedLimit);
    manualDriveSteering = clamp(steering, -1, 1, 0);
    manualDriveThrottle = clamp(throttle, -speedLimit, speedLimit, 0);
    if (els.aiManualDriveKnob) {
      els.aiManualDriveKnob.style.setProperty('--knob-left', `${50 + manualDriveSteering * 50}%`);
      els.aiManualDriveKnob.style.setProperty('--knob-top', `${50 - (manualDriveThrottle / knobScale) * 50}%`);
    }
    updateManualDriveReadout();
    return { steering: manualDriveSteering, throttle: manualDriveThrottle };
  }

  function pointerToManualDrive(event) {
    const rect = els.aiManualDrivePad.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / Math.max(1, rect.width) - 0.5) * 2;
    const y = ((event.clientY - rect.top) / Math.max(1, rect.height) - 0.5) * 2;
    return setManualDriveKnob(x, -y * manualDriveSpeedLimit());
  }

  function fullManualOutputEnabled() {
    return Boolean(els.aiSafetyAck?.checked) && Boolean(els.aiEnableMotor?.checked);
  }

  async function sendFullManualDrive(force = false, source = 'ai-manual-pad') {
    if (!manualDrivePanelActive()) return;
    if (!fullManualOutputEnabled()) {
      updateManualDriveStatus('Manual pad locked: tick both shared safety boxes above first.', 'locked');
      return;
    }
    const now = performance.now();
    if (!force && now - manualDriveLastSentAt < CORRECTION_SEND_INTERVAL_MS) return;
    manualDriveLastSentAt = now;
    try {
      const data = await api('/api/control/manual', {
        method: 'POST',
        body: {
          steering: manualDriveSteering,
          throttle: manualDriveThrottle,
          safety_ack: true,
          enable_motor_output: true,
          source,
        },
      });
      lastAIStatus = { ...(lastAIStatus || {}), running: false, mode: 'manual' };
      if (els.aiRunMode) els.aiRunMode.textContent = 'manual';
      renderAI(data.ai || lastAIStatus || {});
      updateManualDriveStatus(`Manual S ${formatSigned(manualDriveSteering)} / T ${formatSigned(manualDriveThrottle)} sent.`, 'active');
      log('Full manual command sent from AI Mode.', { steering: manualDriveSteering, throttle: manualDriveThrottle, motor: data.motor || {} });
    } catch (err) {
      updateManualDriveStatus(`Manual send failed: ${err.message}`, 'locked');
      log(err.message, err.payload || {});
    }
  }

  async function stopFullManualDrive(reason = 'ai-manual-stop') {
    manualDriveDragging = false;
    manualDriveKeyboardSteering = 0;
    manualDriveKeyboardThrottle = 0;
    manualDriveKeyboardLeftHeld = false;
    manualDriveKeyboardRightHeld = false;
    stopManualDriveKeyboardLoop();
    setManualDriveKnob(0, 0);
    try {
      const data = await api('/api/control/stop', { method: 'POST', body: { reason } });
      renderAI(data.ai || lastAIStatus || {});
      updateManualDriveStatus('Manual STOP sent.', 'ready');
      log('Full manual STOP sent from AI Mode.', data.motor || data || {});
    } catch (err) {
      updateManualDriveStatus(`Manual STOP failed: ${err.message}`, 'locked');
      log(err.message, err.payload || {});
    }
  }

  function manualDriveKeyboardPayload() {
    setManualDriveKnob(manualDriveKeyboardSteering, manualDriveKeyboardThrottle);
    return { steering: manualDriveSteering, throttle: manualDriveThrottle };
  }

  function stopManualDriveKeyboardLoop() {
    if (manualDriveKeyboardLoopHandle) cancelAnimationFrame(manualDriveKeyboardLoopHandle);
    manualDriveKeyboardLoopHandle = 0;
    manualDriveKeyboardLastFrameAt = 0;
  }

  function runManualDriveKeyboardLoop(now) {
    const direction = (manualDriveKeyboardRightHeld ? 1 : 0) - (manualDriveKeyboardLeftHeld ? 1 : 0);
    if (!manualDriveKeyboardLastFrameAt) manualDriveKeyboardLastFrameAt = now;
    const deltaMs = Math.max(0, now - manualDriveKeyboardLastFrameAt);
    manualDriveKeyboardLastFrameAt = now;
    const unitsPerMs = 1 / KEYBOARD_STEERING_FULL_SCALE_MS;
    if (direction) {
      manualDriveKeyboardSteering = clamp(manualDriveKeyboardSteering + direction * deltaMs * unitsPerMs, -1, 1, 0);
    } else {
      const returnStep = deltaMs * unitsPerMs;
      if (Math.abs(manualDriveKeyboardSteering) <= returnStep) manualDriveKeyboardSteering = 0;
      else manualDriveKeyboardSteering -= Math.sign(manualDriveKeyboardSteering) * returnStep;
    }
    manualDriveKeyboardPayload();
    const centred = !direction && Math.abs(manualDriveKeyboardSteering) <= 1e-4;
    sendFullManualDrive(centred, 'ai-manual-keyboard');
    if (direction || !centred) {
      manualDriveKeyboardLoopHandle = requestAnimationFrame(runManualDriveKeyboardLoop);
    } else {
      stopManualDriveKeyboardLoop();
      updateManualDriveStatus(`Keyboard S ${formatSigned(0)} / T ${formatSigned(manualDriveKeyboardThrottle)}`, 'ready');
    }
  }

  function startManualDriveKeyboardLoop() {
    if (manualDriveKeyboardLoopHandle) return;
    manualDriveKeyboardLastFrameAt = 0;
    manualDriveKeyboardLoopHandle = requestAnimationFrame(runManualDriveKeyboardLoop);
  }

  async function sendManualCorrection(force = false, source = 'ai-correction', allowInactive = false) {
    if (!correctionPanelActive && !allowInactive) return;
    const now = performance.now();
    if (!force && now - correctionLastSentAt < CORRECTION_SEND_INTERVAL_MS) return;
    correctionLastSentAt = now;
    try {
      const data = await api('/api/ai/manual-correction', {
        method: 'POST',
        body: { steering: correctionSteering, throttle: correctionThrottle, source },
      });
      renderAI(data.ai || lastAIStatus || {});
      updateCorrectionStatus(`Correction S ${formatSigned(correctionSteering)} / T ${formatSigned(correctionThrottle)} · correction ${Math.round(clamp(els.aiManualMix?.value || 50, 0, 100, 50))}%`, 'active');
    } catch (err) {
      updateCorrectionStatus(`Correction send failed: ${err.message}`, 'locked');
      log(err.message, err.payload || {});
    }
  }

  function shortcutBlocked() {
    const active = document.activeElement;
    if (!active || active === document.body || active === document.documentElement || active === els.aiCorrectionPad || active === els.aiManualDrivePad) return false;
    const tag = String(active.tagName || '').toLowerCase();
    if (tag === 'input') {
      const type = String(active.type || '').toLowerCase();
      return !['checkbox', 'button', 'submit', 'reset'].includes(type);
    }
    if (['select', 'textarea'].includes(tag)) return true;
    return Boolean(active.isContentEditable);
  }

  function correctionKeyboardPayload() {
    setCorrectionKnob(correctionKeyboardSteering, correctionKeyboardThrottle);
    return { steering: correctionSteering, throttle: correctionThrottle };
  }

  function stopCorrectionKeyboardLoop() {
    if (correctionKeyboardLoopHandle) cancelAnimationFrame(correctionKeyboardLoopHandle);
    correctionKeyboardLoopHandle = 0;
    correctionKeyboardLastFrameAt = 0;
  }

  function runCorrectionKeyboardLoop(now) {
    const direction = (correctionKeyboardRightHeld ? 1 : 0) - (correctionKeyboardLeftHeld ? 1 : 0);
    if (!correctionKeyboardLastFrameAt) correctionKeyboardLastFrameAt = now;
    const deltaMs = Math.max(0, now - correctionKeyboardLastFrameAt);
    correctionKeyboardLastFrameAt = now;
    const unitsPerMs = 1 / KEYBOARD_STEERING_FULL_SCALE_MS;
    if (direction) {
      correctionKeyboardSteering = clamp(correctionKeyboardSteering + direction * deltaMs * unitsPerMs, -1, 1, 0);
    } else {
      const returnStep = deltaMs * unitsPerMs;
      if (Math.abs(correctionKeyboardSteering) <= returnStep) correctionKeyboardSteering = 0;
      else correctionKeyboardSteering -= Math.sign(correctionKeyboardSteering) * returnStep;
    }
    correctionKeyboardPayload();
    const centred = !direction && Math.abs(correctionKeyboardSteering) <= 1e-4;
    sendManualCorrection(centred, 'ai-correction-keyboard');
    if (direction || !centred) {
      correctionKeyboardLoopHandle = requestAnimationFrame(runCorrectionKeyboardLoop);
    } else {
      stopCorrectionKeyboardLoop();
      updateCorrectionStatus(`Keyboard S ${formatSigned(0)} / T ${formatSigned(correctionKeyboardThrottle)}`, 'ready');
    }
  }

  function startCorrectionKeyboardLoop() {
    if (correctionKeyboardLoopHandle) return;
    correctionKeyboardLastFrameAt = 0;
    correctionKeyboardLoopHandle = requestAnimationFrame(runCorrectionKeyboardLoop);
  }

  async function resetManualCorrection(reason = 'ai-correction-reset', allowInactive = false) {
    correctionKeyboardSteering = 0;
    correctionKeyboardThrottle = 0;
    correctionKeyboardLeftHeld = false;
    correctionKeyboardRightHeld = false;
    stopCorrectionKeyboardLoop();
    setCorrectionKnob(0, 0);
    await sendManualCorrection(true, reason, allowInactive);
    updateCorrectionStatus('Correction centred.', 'ready');
  }

  function setPreview(mode, src = '') {
    if (!els.aiPreviewFrame || !els.aiPreviewImage || !els.aiPreviewCaption) return;
    els.aiPreviewFrame.dataset.previewState = mode;
    els.aiPreviewFrame.dataset.previewMode = mode;
    els.aiPreviewImage.dataset.previewMode = mode;
    els.aiPreviewImage.src = src || IDLE_PREVIEW_SRC;
    els.aiPreviewCaption.textContent = mode === 'live'
      ? 'Live stream running. The overlay is drawn from the latest corrected AI safe command.'
      : mode === 'snapshot'
        ? 'Snapshot preview loaded. Run AI preview/predict once to update the AI model overlay.'
        : mode === 'error'
          ? 'Preview error.'
          : 'Preview is idle. Start live first, then use AI preview to see the model-predicted safe path overlay before enabling AI drive.';
  }

  async function saveConfig() {
    try {
      const data = await api('/api/ai/config', { method: 'POST', body: collectConfig() });
      renderAI(data.ai || {});
      log('AI settings saved.', data.ai || {});
    } catch (err) {
      log(err.message, err.payload || {});
    }
  }

  async function loadModel() {
    await saveConfig();
    const modelId = els.aiModelSelect?.value || '';
    try {
      const data = await api('/api/ai/load-model', { method: 'POST', body: { model_id: modelId } });
      renderAI(data.ai || {});
      log('Model loaded.', data.ai || {});
    } catch (err) {
      renderAI((err.payload || {}).ai || {});
      log(err.message, err.payload || {});
    }
  }

  async function uploadModel() {
    const file = els.aiModelUploadFile?.files?.[0];
    if (!file) {
      log('Choose a piTrainer .keras or .tflite model file first.');
      return;
    }
    const form = new FormData();
    form.append('model', file, file.name);
    try {
      const response = await fetch('/api/ai/upload-model', { method: 'POST', body: form });
      const data = await response.json().catch(() => ({ ok: false, message: `HTTP ${response.status}` }));
      if (!response.ok || !data.ok) {
        const err = new Error(data.message || 'Model upload failed.');
        err.payload = data;
        throw err;
      }
      log('Model uploaded.', data.model || {});
      await refreshModels();
      if (els.aiModelSelect && data.model?.id) els.aiModelSelect.value = data.model.id;
      if (els.aiModelUploadFile) els.aiModelUploadFile.value = '';
      renderAI(data.ai || lastAIStatus || {});
    } catch (err) {
      log(err.message, err.payload || {});
    }
  }

  async function deleteSelectedModel() {
    const modelId = els.aiModelSelect?.value || '';
    if (!modelId) {
      log('No model selected to delete.');
      return;
    }
    const ok = window.confirm(`Delete model from PiSD/models?\n\n${modelId}`);
    if (!ok) return;
    try {
      const data = await api('/api/ai/delete-model', { method: 'POST', body: { model_id: modelId } });
      log('Model deleted.', { deleted_model_id: data.deleted_model_id, unloaded_selected_model: data.unloaded_selected_model });
      await refreshModels();
      renderAI(data.ai || {});
    } catch (err) {
      renderAI((err.payload || {}).ai || lastAIStatus || {});
      log(err.message, err.payload || {});
    }
  }

  async function startAI(mode) {
    const safetyAck = Boolean(els.aiSafetyAck?.checked);
    const enableMotorOutput = Boolean(els.aiEnableMotor?.checked);
    await saveConfig();
    try {
      const data = await api('/api/ai/start', {
        method: 'POST',
        body: {
          mode,
          safety_ack: safetyAck,
          enable_motor_output: enableMotorOutput,
        },
      });
      renderAI(data.ai || {});
      log(mode === 'drive' ? 'AI drive started.' : 'AI preview started.', data.ai || {});
      startStatusLoop();
    } catch (err) {
      renderAI((err.payload || {}).ai || {});
      log(err.message, err.payload || {});
    }
  }

  async function stopAI() {
    try {
      const data = await api('/api/ai/stop', { method: 'POST', body: {} });
      renderAI(data.ai || {});
      log('AI mode stopped.', data.ai || {});
    } catch (err) {
      log(err.message, err.payload || {});
    }
  }

  async function predictOnce() {
    try {
      const data = await api('/api/ai/predict-once', { method: 'POST', body: {} });
      renderAI(data.ai || {});
      log('One AI prediction completed.', { raw: data.raw_prediction, corrected: data.corrected_command || data.mixed_command, safe: data.safe_command });
    } catch (err) {
      renderAI((err.payload || {}).ai || {});
      log(err.message, err.payload || {});
    }
  }

  async function saveAISnapshot() {
    try {
      await api('/api/camera/start', { method: 'POST', body: {} }).catch(() => null);
      const data = await api('/api/recording/capture', { method: 'POST', body: { label: 'ai_mode_capture' } });
      renderRecording(data.recording || {});
      setPreview('snapshot', `/api/camera/frame.jpg?t=${Date.now()}`);
      log('AI snapshot saved.', data.record || data.recording || {});
    } catch (err) {
      log(err.message, err.payload || {});
    }
  }

  async function toggleAIRecording() {
    try {
      if (recordingRunning) {
        const data = await api('/api/recording/stop', { method: 'POST', body: {} });
        renderRecording(data.recording || {});
        log('AI recording stopped.', data.stopped_session || data.recording || {});
      } else {
        await api('/api/camera/start', { method: 'POST', body: {} }).catch(() => null);
        const fps = clamp(Number(els.aiUpdateHz?.value || 12), 0.2, 30, 12);
        const data = await api('/api/recording/start', { method: 'POST', body: { label: 'ai_mode', fps } });
        renderRecording(data.recording || {});
        log('AI recording started.', data.recording?.active_session || data.recording || {});
      }
      await refreshStatus();
    } catch (err) {
      renderRecording((err.payload || {}).recording || {});
      log(err.message, err.payload || {});
    }
  }

  function startStatusLoop() {
    if (statusTimer) return;
    statusTimer = setInterval(async () => {
      const data = await refreshStatus();
      if (!((data || {}).ai || {}).running) {
        clearInterval(statusTimer);
        statusTimer = null;
      }
    }, 250);
  }

  function wireRanges() {
    [
      ['aiMaxThrottle', 'aiMaxThrottleOut', 2], ['aiMaxSteering', 'aiMaxSteeringOut', 2], ['aiFixedThrottle', 'aiFixedThrottleOut', 2],
      ['aiUpdateHz', 'aiUpdateHzOut', 0], ['aiSteerSmooth', 'aiSteerSmoothOut', 2], ['aiThrottleSmooth', 'aiThrottleSmoothOut', 2],
    ].forEach(([inputId, outId, digits]) => {
      els[inputId]?.addEventListener('input', () => { if (els[outId]) els[outId].textContent = fmt(els[inputId].value, digits); });
    });
    els.aiManualMix?.addEventListener('input', () => setPercentRange('aiManualMix', 'aiManualMixOut', els.aiManualMix.value || 50));
    els.aiManualMix?.addEventListener('change', saveConfig);
    els.aiManualDriveSpeed?.addEventListener('input', () => setManualDriveKnob(manualDriveSteering, manualDriveThrottle));
  }

  function bindCorrectionPad() {
    if (els.aiLimiterTab) els.aiLimiterTab.addEventListener('click', () => setOutputPanel('limiter', true));
    if (els.aiCorrectionTab) els.aiCorrectionTab.addEventListener('click', () => setOutputPanel('correction', true));
    if (els.aiManualDriveTab) els.aiManualDriveTab.addEventListener('click', () => setOutputPanel('manual', true));
    if (els.aiCorrectionPad) {
      els.aiCorrectionPad.addEventListener('pointerdown', (event) => {
        if (!correctionPanelActive) return;
        event.preventDefault();
        correctionDragging = true;
        els.aiCorrectionPad.setPointerCapture(event.pointerId);
        pointerToCorrection(event);
        sendManualCorrection(true, 'ai-correction-drag');
      });
      els.aiCorrectionPad.addEventListener('pointermove', (event) => {
        if (!correctionDragging || !correctionPanelActive) return;
        event.preventDefault();
        pointerToCorrection(event);
        sendManualCorrection(false, 'ai-correction-drag');
      });
      const release = (event) => {
        if (!correctionDragging) return;
        correctionDragging = false;
        try { els.aiCorrectionPad.releasePointerCapture(event.pointerId); } catch (_err) {}
        resetManualCorrection('ai-correction-drag-release');
      };
      els.aiCorrectionPad.addEventListener('pointerup', release);
      els.aiCorrectionPad.addEventListener('pointercancel', release);
      els.aiCorrectionPad.addEventListener('mouseleave', () => {
        if (!correctionDragging) return;
        correctionDragging = false;
        resetManualCorrection('ai-correction-drag-leave');
      });
    }
    if (els.aiManualDrivePad) {
      els.aiManualDrivePad.addEventListener('pointerdown', (event) => {
        if (!manualDrivePanelActive()) return;
        event.preventDefault();
        manualDriveDragging = true;
        els.aiManualDrivePad.setPointerCapture(event.pointerId);
        pointerToManualDrive(event);
        sendFullManualDrive(true, 'ai-manual-drag');
      });
      els.aiManualDrivePad.addEventListener('pointermove', (event) => {
        if (!manualDriveDragging || !manualDrivePanelActive()) return;
        event.preventDefault();
        pointerToManualDrive(event);
        sendFullManualDrive(false, 'ai-manual-drag');
      });
      const manualRelease = (event) => {
        if (!manualDriveDragging) return;
        try { els.aiManualDrivePad.releasePointerCapture(event.pointerId); } catch (_err) {}
        stopFullManualDrive('ai-manual-drag-release');
      };
      els.aiManualDrivePad.addEventListener('pointerup', manualRelease);
      els.aiManualDrivePad.addEventListener('pointercancel', manualRelease);
      els.aiManualDrivePad.addEventListener('mouseleave', () => {
        if (!manualDriveDragging) return;
        stopFullManualDrive('ai-manual-drag-leave');
      });
    }
  }

  function bindKeyboardShortcuts() {
    document.addEventListener('keydown', (event) => {
      if (shortcutBlocked()) return;
      const key = event.key;
      const shortcut = String(key || '').toLowerCase();
      const isRecordOrSnapshot = shortcut === 'r' || shortcut === 's';
      const isPanelDriveKey = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(key);
      const isCorrectionKey = correctionPanelActive && isPanelDriveKey;
      const isManualDriveKey = manualDrivePanelActive() && isPanelDriveKey;
      if (!isRecordOrSnapshot && !isCorrectionKey && !isManualDriveKey) return;
      event.preventDefault();
      if (shortcut === 'r') {
        if (!event.repeat) toggleAIRecording();
        return;
      }
      if (shortcut === 's') {
        if (!event.repeat) saveAISnapshot();
        return;
      }
      if (manualDrivePanelActive()) {
        if (key === ' ') {
          if (!event.repeat) stopFullManualDrive('ai-manual-space');
          return;
        }
        if (key === 'ArrowUp' || key === 'ArrowDown') {
          if (event.repeat) return;
          const limit = manualDriveSpeedLimit();
          manualDriveKeyboardThrottle = clamp(manualDriveKeyboardThrottle + (key === 'ArrowUp' ? KEYBOARD_THROTTLE_STEP : -KEYBOARD_THROTTLE_STEP), -limit, limit, 0);
          manualDriveKeyboardPayload();
          sendFullManualDrive(true, 'ai-manual-keyboard');
          return;
        }
        if (key === 'ArrowLeft') {
          manualDriveKeyboardLeftHeld = true;
          startManualDriveKeyboardLoop();
          return;
        }
        if (key === 'ArrowRight') {
          manualDriveKeyboardRightHeld = true;
          startManualDriveKeyboardLoop();
        }
        return;
      }
      if (!correctionPanelActive) return;
      if (key === ' ') {
        if (!event.repeat) resetManualCorrection('ai-correction-space');
        return;
      }
      if (key === 'ArrowUp' || key === 'ArrowDown') {
        if (event.repeat) return;
        correctionKeyboardThrottle = clamp(correctionKeyboardThrottle + (key === 'ArrowUp' ? KEYBOARD_THROTTLE_STEP : -KEYBOARD_THROTTLE_STEP), -1, 1, 0);
        correctionKeyboardPayload();
        sendManualCorrection(true, 'ai-correction-keyboard');
        return;
      }
      if (key === 'ArrowLeft') {
        correctionKeyboardLeftHeld = true;
        startCorrectionKeyboardLoop();
        return;
      }
      if (key === 'ArrowRight') {
        correctionKeyboardRightHeld = true;
        startCorrectionKeyboardLoop();
      }
    }, { passive: false });

    document.addEventListener('keyup', (event) => {
      if (manualDrivePanelActive() && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
        event.preventDefault();
        if (event.key === 'ArrowLeft') manualDriveKeyboardLeftHeld = false;
        if (event.key === 'ArrowRight') manualDriveKeyboardRightHeld = false;
        if (!manualDriveKeyboardLeftHeld && !manualDriveKeyboardRightHeld) startManualDriveKeyboardLoop();
        return;
      }
      if (!correctionPanelActive || (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')) return;
      event.preventDefault();
      if (event.key === 'ArrowLeft') correctionKeyboardLeftHeld = false;
      if (event.key === 'ArrowRight') correctionKeyboardRightHeld = false;
      if (!correctionKeyboardLeftHeld && !correctionKeyboardRightHeld) startCorrectionKeyboardLoop();
    }, { passive: false });

    window.addEventListener('blur', () => {
      if (manualDrivePanelActive()) stopFullManualDrive('ai-manual-blur');
      if (correctionPanelActive) resetManualCorrection('ai-correction-blur');
    });
  }

  function bind() {
    els.aiOverlayToggle?.addEventListener('click', () => setOverlayEnabled(!overlayEnabled));
    els.aiRefreshModels?.addEventListener('click', refreshModels);
    els.aiLoadModel?.addEventListener('click', loadModel);
    els.aiPredictOnce?.addEventListener('click', predictOnce);
    els.aiUploadModel?.addEventListener('click', uploadModel);
    els.aiDeleteModel?.addEventListener('click', deleteSelectedModel);
    els.aiSaveConfig?.addEventListener('click', saveConfig);
    els.aiStartPreview?.addEventListener('click', () => startAI('preview'));
    els.aiStartDrive?.addEventListener('click', () => startAI('drive'));
    els.aiStop?.addEventListener('click', stopAI);
    els.aiStopAll?.addEventListener('click', async () => { await stopAI(); await api('/api/control/stop', { method: 'POST', body: {} }).catch(() => null); });
    els.aiRefreshStatus?.addEventListener('click', refreshStatus);
    els.aiSaveSnapshot?.addEventListener('click', saveAISnapshot);
    els.aiRecordToggle?.addEventListener('click', toggleAIRecording);
    els.aiManualDriveStop?.addEventListener('click', () => stopFullManualDrive('ai-manual-stop-button'));
    els.aiEnableMotor?.addEventListener('change', () => { if (!els.aiEnableMotor.checked && manualDrivePanelActive()) stopFullManualDrive('ai-manual-disabled'); });
    els.aiSafetyAck?.addEventListener('change', () => { if (!els.aiSafetyAck.checked && manualDrivePanelActive()) stopFullManualDrive('ai-manual-safety-cleared'); });
    bindCorrectionPad();
    bindKeyboardShortcuts();
    els.aiLive?.addEventListener('click', async () => { await api('/api/camera/start', { method: 'POST', body: {} }).catch((err) => log(err.message, err.payload)); setPreview('live', `/video_feed?t=${Date.now()}`); });
    els.aiStopCamera?.addEventListener('click', async () => { await api('/api/camera/stop', { method: 'POST', body: {} }).catch((err) => log(err.message, err.payload)); setPreview('idle', ''); });
    window.addEventListener('pagehide', () => {
      const zero = new Blob([JSON.stringify({ steering: 0, throttle: 0, source: 'ai-correction-pagehide' })], { type: 'application/json' });
      navigator.sendBeacon?.('/api/ai/manual-correction', zero);
      if (manualDrivePanelActive()) navigator.sendBeacon?.('/api/control/stop', new Blob([JSON.stringify({ reason: 'ai-manual-pagehide' })], { type: 'application/json' }));
      if (aiRunning) navigator.sendBeacon?.('/api/ai/stop', new Blob([JSON.stringify({})], { type: 'application/json' }));
    });
    document.addEventListener('visibilitychange', () => { if (document.hidden) { resetManualCorrection('ai-correction-hidden'); if (manualDrivePanelActive()) stopFullManualDrive('ai-manual-hidden'); if (aiRunning) navigator.sendBeacon?.('/api/ai/stop', new Blob([JSON.stringify({})], { type: 'application/json' })); } });
  }

  enforceFullScaleThrottleRanges();
  setPreview('idle', '');
  setOverlayEnabled(true);
  updateOverlayMotorSettings(initial.motor || {});
  setCorrectionKnob(0, 0);
  setManualDriveKnob(0, 0);
  renderAI((initial.ai_mode || {}));
  renderRecording(initial.recording || {});
  wireRanges();
  bind();
  refreshModels().then(() => refreshStatus());
})();
