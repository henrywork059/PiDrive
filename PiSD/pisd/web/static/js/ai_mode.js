(() => {
  const initial = JSON.parse(document.getElementById('aiModeInitialStatus')?.textContent || '{}');
  const els = {};
  const ids = [
    'aiGlobalCode', 'aiRunMode', 'aiModelReady', 'aiPreviewImage', 'aiPreviewCaption', 'aiStartCamera', 'aiSnapshot', 'aiLive', 'aiStopCamera',
    'aiRefreshModels', 'aiModelSelect', 'aiLoadModel', 'aiPredictOnce', 'aiSelectedModel', 'aiBackend', 'aiInputShape', 'aiModelsDir',
    'aiSafetyAck', 'aiEnableMotor', 'aiOutputMode', 'aiMaxThrottle', 'aiMaxThrottleOut', 'aiMaxSteering', 'aiMaxSteeringOut',
    'aiFixedThrottle', 'aiFixedThrottleOut', 'aiUpdateHz', 'aiUpdateHzOut', 'aiSteerSmooth', 'aiSteerSmoothOut', 'aiThrottleSmooth',
    'aiThrottleSmoothOut', 'aiSaveConfig', 'aiStartPreview', 'aiStartDrive', 'aiStop', 'aiStopAll', 'aiRawSteering', 'aiRawThrottle',
    'aiSafeSteering', 'aiSafeThrottle', 'aiLeftMotor', 'aiRightMotor', 'aiInferenceMs', 'aiLoopHz', 'aiRefreshStatus', 'aiLog'
  ];
  ids.forEach((id) => { els[id] = document.getElementById(id); });

  let statusTimer = null;
  let aiRunning = false;

  function fmt(value, digits = 2) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits) : '-';
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
      motor_output_enabled: Boolean(els.aiEnableMotor?.checked),
    };
  }

  function setRange(id, outputId, value, digits = 2) {
    if (els[id]) els[id].value = String(value);
    if (els[outputId]) els[outputId].textContent = fmt(value, digits);
  }

  function renderConfig(config = {}) {
    if (els.aiOutputMode) els.aiOutputMode.value = config.output_mode || 'steering_and_throttle';
    if (els.aiEnableMotor) els.aiEnableMotor.checked = Boolean(config.motor_output_enabled);
    setRange('aiMaxThrottle', 'aiMaxThrottleOut', config.max_throttle ?? 0.22);
    setRange('aiMaxSteering', 'aiMaxSteeringOut', config.max_steering ?? 0.70);
    setRange('aiFixedThrottle', 'aiFixedThrottleOut', config.fixed_throttle ?? 0.16);
    setRange('aiUpdateHz', 'aiUpdateHzOut', config.update_hz ?? 8, 0);
    setRange('aiSteerSmooth', 'aiSteerSmoothOut', config.steering_smoothing ?? 0.35);
    setRange('aiThrottleSmooth', 'aiThrottleSmoothOut', config.throttle_smoothing ?? 0.25);
  }

  function renderAI(ai = {}) {
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
    if (els.aiLeftMotor) els.aiLeftMotor.textContent = fmt(motor.left);
    if (els.aiRightMotor) els.aiRightMotor.textContent = fmt(motor.right);
    if (els.aiInferenceMs) els.aiInferenceMs.textContent = `${fmt(ai.last_inference_ms, 1)} ms`;
    if (els.aiLoopHz) els.aiLoopHz.textContent = `${fmt(ai.loop_hz, 1)} Hz`;
    if (ai.settings) renderConfig(ai.settings);
  }

  async function refreshStatus() {
    try {
      const data = await api('/api/ai/status');
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
    const box = document.querySelector('.ai-preview-box');
    if (!box || !els.aiPreviewImage || !els.aiPreviewCaption) return;
    box.dataset.previewState = mode;
    if (src) els.aiPreviewImage.src = src;
    els.aiPreviewCaption.textContent = mode === 'live' ? 'Live stream running.' : mode === 'snapshot' ? 'Snapshot preview loaded.' : mode === 'error' ? 'Preview error.' : 'Preview is idle.';
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
    await saveConfig();
    try {
      const data = await api('/api/ai/start', {
        method: 'POST',
        body: {
          mode,
          safety_ack: Boolean(els.aiSafetyAck?.checked),
          enable_motor_output: Boolean(els.aiEnableMotor?.checked),
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
  renderAI((initial.ai_mode || {}));
  wireRanges();
  bind();
  refreshModels().then(() => refreshStatus());
})();
