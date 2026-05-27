(() => {
  const initial = JSON.parse(document.getElementById('aiModeInitialStatus')?.textContent || '{}');
  const els = {};
  const ids = [
    'aiGlobalCode', 'aiRunMode', 'aiModelReady', 'aiPreviewFrame', 'aiPreviewImage', 'aiPreviewCaption', 'aiStartCamera', 'aiSnapshot', 'aiLive', 'aiStopCamera',
    'aiOverlayToggle', 'aiOverlayMode', 'aiOverlayCurveLabel', 'aiOverlayCar', 'aiOverlaySurface', 'aiOverlayPathWide', 'aiOverlayPathGuide', 'aiOverlayPath',
    'aiOverlayEndpoint', 'aiOverlayStartPoint', 'aiOverlayThrottleFill', 'aiOverlaySteeringFill', 'aiOverlayThrottleValue', 'aiOverlaySteeringValue',
    'aiOverlayRawSteering', 'aiOverlayRawThrottle', 'aiOverlayLeftValue', 'aiOverlayRightValue',
    'aiRefreshModels', 'aiModelSelect', 'aiLoadModel', 'aiPredictOnce', 'aiSelectedModel', 'aiBackend', 'aiInputShape', 'aiModelsDir',
    'aiSafetyAck', 'aiEnableMotor', 'aiOutputMode', 'aiMaxThrottle', 'aiMaxThrottleOut', 'aiMaxSteering', 'aiMaxSteeringOut',
    'aiFixedThrottle', 'aiFixedThrottleOut', 'aiUpdateHz', 'aiUpdateHzOut', 'aiSteerSmooth', 'aiSteerSmoothOut', 'aiThrottleSmooth',
    'aiThrottleSmoothOut', 'aiSaveConfig', 'aiStartPreview', 'aiStartDrive', 'aiStop', 'aiStopAll', 'aiRawSteering', 'aiRawThrottle',
    'aiSafeSteering', 'aiSafeThrottle', 'aiLeftMotor', 'aiRightMotor', 'aiInferenceMs', 'aiLoopHz', 'aiRefreshStatus', 'aiLog'
  ];
  ids.forEach((id) => { els[id] = document.getElementById(id); });

  const IDLE_PREVIEW_SRC = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1280 720'%3E%3Crect width='1280' height='720' fill='%23020617'/%3E%3Ctext x='640' y='340' fill='%2394a3b8' font-family='Arial,sans-serif' font-size='42' text-anchor='middle'%3EAI preview idle%3C/text%3E%3Ctext x='640' y='398' fill='%2364748b' font-family='Arial,sans-serif' font-size='26' text-anchor='middle'%3EStart camera / live, then run AI preview%3C/text%3E%3C/svg%3E";
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
  let overlayEnabled = true;
  let lastAIStatus = initial.ai_mode || {};
  let aiMotorEnableInitialised = false;
  let latestMotorSettings = { ...DEFAULT_MOTOR_SETTINGS };

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
      update_hz: Number(els.aiUpdateHz?.value || 8),
      steering_smoothing: Number(els.aiSteerSmooth?.value || 0.35),
      throttle_smoothing: Number(els.aiThrottleSmooth?.value || 0.25),
    };
  }

  function setRange(id, outputId, value, digits = 2) {
    if (els[id]) els[id].value = String(value);
    if (els[outputId]) els[outputId].textContent = fmt(value, digits);
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
    setRange('aiUpdateHz', 'aiUpdateHzOut', config.update_hz ?? 8, 0);
    setRange('aiSteerSmooth', 'aiSteerSmoothOut', config.steering_smoothing ?? 0.35);
    setRange('aiThrottleSmooth', 'aiThrottleSmoothOut', config.throttle_smoothing ?? 0.25);
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
    const safe = ai.last_safe_command || {};
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
    const safe = ai.last_safe_command || {};
    const motor = ai.last_motor_output || {};
    if (els.aiRunMode) els.aiRunMode.textContent = ai.mode || 'idle';
    if (els.aiModelReady) els.aiModelReady.textContent = ai.model_ready ? 'ready' : (ai.model_loaded ? 'loaded' : 'not loaded');
    if (els.aiSelectedModel) els.aiSelectedModel.textContent = ai.model_id || 'none';
    if (els.aiBackend) els.aiBackend.textContent = ai.backend || 'none';
    if (els.aiModelsDir) els.aiModelsDir.textContent = ai.models_dir || 'models';
    const input = ai.input_size || {};
    if (els.aiInputShape) els.aiInputShape.textContent = input.width ? `${input.width} × ${input.height}` : '-';
    if (els.aiRawSteering) els.aiRawSteering.textContent = fmt(raw.steering);
    if (els.aiRawThrottle) els.aiRawThrottle.textContent = fmt(raw.throttle);
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
    if (ai.settings) renderConfig(ai.settings);
    updateAIOverlay(ai);
  }

  async function refreshStatus() {
    try {
      const data = await api('/api/ai/status');
      updateOverlayMotorSettings(data.motor || {});
      renderAI(data.ai || {});
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
  }

  function setPreview(mode, src = '') {
    if (!els.aiPreviewFrame || !els.aiPreviewImage || !els.aiPreviewCaption) return;
    els.aiPreviewFrame.dataset.previewState = mode;
    els.aiPreviewFrame.dataset.previewMode = mode;
    els.aiPreviewImage.dataset.previewMode = mode;
    els.aiPreviewImage.src = src || IDLE_PREVIEW_SRC;
    els.aiPreviewCaption.textContent = mode === 'live'
      ? 'Live stream running. The overlay is drawn from the latest AI safe command, not from manual control.'
      : mode === 'snapshot'
        ? 'Snapshot preview loaded. Run AI preview/predict once to update the AI model overlay.'
        : mode === 'error'
          ? 'Preview error.'
          : 'Preview is idle. Start camera/live first, then use AI preview to see the model-predicted safe path overlay before enabling AI drive.';
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
      log('One AI prediction completed.', { raw: data.raw_prediction, safe: data.safe_command });
    } catch (err) {
      renderAI((err.payload || {}).ai || {});
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
    }, 750);
  }

  function wireRanges() {
    [
      ['aiMaxThrottle', 'aiMaxThrottleOut', 2], ['aiMaxSteering', 'aiMaxSteeringOut', 2], ['aiFixedThrottle', 'aiFixedThrottleOut', 2],
      ['aiUpdateHz', 'aiUpdateHzOut', 0], ['aiSteerSmooth', 'aiSteerSmoothOut', 2], ['aiThrottleSmooth', 'aiThrottleSmoothOut', 2],
    ].forEach(([inputId, outId, digits]) => {
      els[inputId]?.addEventListener('input', () => { if (els[outId]) els[outId].textContent = fmt(els[inputId].value, digits); });
    });
  }

  function bind() {
    els.aiOverlayToggle?.addEventListener('click', () => setOverlayEnabled(!overlayEnabled));
    els.aiRefreshModels?.addEventListener('click', refreshModels);
    els.aiLoadModel?.addEventListener('click', loadModel);
    els.aiPredictOnce?.addEventListener('click', predictOnce);
    els.aiSaveConfig?.addEventListener('click', saveConfig);
    els.aiStartPreview?.addEventListener('click', () => startAI('preview'));
    els.aiStartDrive?.addEventListener('click', () => startAI('drive'));
    els.aiStop?.addEventListener('click', stopAI);
    els.aiStopAll?.addEventListener('click', async () => { await stopAI(); await api('/api/control/stop', { method: 'POST', body: {} }).catch(() => null); });
    els.aiRefreshStatus?.addEventListener('click', refreshStatus);
    els.aiStartCamera?.addEventListener('click', async () => { await api('/api/camera/start', { method: 'POST', body: {} }).catch((err) => log(err.message, err.payload)); setPreview('snapshot', `/api/camera/frame.jpg?t=${Date.now()}`); });
    els.aiSnapshot?.addEventListener('click', () => setPreview('snapshot', `/api/camera/frame.jpg?t=${Date.now()}`));
    els.aiLive?.addEventListener('click', async () => { await api('/api/camera/start', { method: 'POST', body: {} }).catch((err) => log(err.message, err.payload)); setPreview('live', `/video_feed?t=${Date.now()}`); });
    els.aiStopCamera?.addEventListener('click', async () => { await api('/api/camera/stop', { method: 'POST', body: {} }).catch((err) => log(err.message, err.payload)); setPreview('idle', ''); });
    window.addEventListener('pagehide', () => { if (aiRunning) navigator.sendBeacon?.('/api/ai/stop', new Blob([JSON.stringify({})], { type: 'application/json' })); });
    document.addEventListener('visibilitychange', () => { if (document.hidden && aiRunning) navigator.sendBeacon?.('/api/ai/stop', new Blob([JSON.stringify({})], { type: 'application/json' })); });
  }

  enforceFullScaleThrottleRanges();
  setPreview('idle', '');
  setOverlayEnabled(true);
  updateOverlayMotorSettings(initial.motor || {});
  renderAI((initial.ai_mode || {}));
  wireRanges();
  bind();
  refreshModels().then(() => refreshStatus());
})();
