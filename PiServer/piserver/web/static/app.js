const gridCols = 36;
const gridRows = 20;
const layoutKeyPrefix = "PiServerLayout:v0_2_20:";
const STEP_INTERVAL_MS = 80;
const STEP_SIZE = 0.1;
const SMOOTH_STEP_STEER = 0.07;
const SMOOTH_STEP_THROTTLE = 0.07;

const pagePanels = {
  manual: ["status", "estop", "viewer", "runtime", "manual", "record"],
  training: ["status", "estop", "viewer", "runtime", "model", "manual", "record"],
  auto: ["status", "estop", "viewer", "runtime", "model", "record"],
  camera: ["status", "estop", "viewer", "camera"],
  motor: ["status", "estop", "viewer", "motor"]
};

const defaultLayouts = {
  manual: {
    status: { c: 1, r: 1, w: 30, h: 5 },
    estop: { c: 31, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 21, h: 11 },
    runtime: { c: 22, r: 6, w: 15, h: 5 },
    manual: { c: 22, r: 11, w: 15, h: 6 },
    record: { c: 1, r: 17, w: 21, h: 4 }
  },
  training: {
    status: { c: 1, r: 1, w: 30, h: 5 },
    estop: { c: 31, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 18, h: 10 },
    runtime: { c: 19, r: 6, w: 18, h: 4 },
    model: { c: 19, r: 10, w: 18, h: 4 },
    manual: { c: 19, r: 14, w: 18, h: 7 },
    record: { c: 1, r: 16, w: 18, h: 5 }
  },
  auto: {
    status: { c: 1, r: 1, w: 30, h: 5 },
    estop: { c: 31, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 21, h: 11 },
    runtime: { c: 22, r: 6, w: 15, h: 5 },
    model: { c: 22, r: 11, w: 15, h: 6 },
    record: { c: 1, r: 17, w: 21, h: 4 }
  },
  camera: {
    status: { c: 1, r: 1, w: 30, h: 5 },
    estop: { c: 31, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 20, h: 15 },
    camera: { c: 21, r: 6, w: 16, h: 15 }
  },
  motor: {
    status: { c: 1, r: 1, w: 30, h: 5 },
    estop: { c: 31, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 20, h: 15 },
    motor: { c: 21, r: 6, w: 16, h: 15 }
  }
};

const state = {
  page: "manual",
  manualSteering: 0,
  manualThrottle: 0,
  targetSteering: 0,
  targetThrottle: 0,
  maxThrottle: 0.55,
  steerMix: 0.5,
  steerBias: 0,
  dragging: null,
  resizing: null,
  latestStatus: null,
  statusTimer: null,
  cameraConfig: null,
  motorConfig: null,
  motorFormDirty: false,
  previewTimer: null,
  previewActive: false,
  previewInFlight: false,
  previewObjectUrl: null,
  stepTimer: null,
  stepInputs: { up: false, down: false, left: false, right: false },
  pointerControl: { active: false, id: null },
  estopEnabled: false,
  recordEnabled: false,
  recordPending: false,
  lastControlSentAt: 0,
  lastSentSteering: 0,
  lastSentThrottle: 0,
  lastSentPage: "manual"
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function moveTowards(current, target, maxDelta) {
  if (Math.abs(target - current) <= maxDelta) return target;
  return current + Math.sign(target - current) * maxDelta;
}

function almostEqual(a, b, epsilon = 0.0001) {
  return Math.abs(Number(a || 0) - Number(b || 0)) <= epsilon;
}

function panelEls() {
  return Array.from(document.querySelectorAll(".dock-panel"));
}

function layoutStorageKey(page) {
  return `${layoutKeyPrefix}${page}`;
}

function deepCloneLayout(layout) {
  return JSON.parse(JSON.stringify(layout));
}

function loadLayout(page) {
  try {
    const raw = localStorage.getItem(layoutStorageKey(page));
    if (!raw) return deepCloneLayout(defaultLayouts[page] || defaultLayouts.manual);
    const parsed = JSON.parse(raw);
    return Object.assign(deepCloneLayout(defaultLayouts[page] || defaultLayouts.manual), parsed);
  } catch {
    return deepCloneLayout(defaultLayouts[page] || defaultLayouts.manual);
  }
}

function saveLayout(page, layout) {
  localStorage.setItem(layoutStorageKey(page), JSON.stringify(layout));
}

function readPanelBox(panel) {
  const style = getComputedStyle(panel);
  return {
    c: Number(style.getPropertyValue("--c")) || 1,
    r: Number(style.getPropertyValue("--r")) || 1,
    w: Number(style.getPropertyValue("--w")) || 8,
    h: Number(style.getPropertyValue("--h")) || 4
  };
}

function setPanelBox(panel, box) {
  panel.style.setProperty("--c", box.c);
  panel.style.setProperty("--r", box.r);
  panel.style.setProperty("--w", box.w);
  panel.style.setProperty("--h", box.h);
}

function currentLayout() {
  const out = {};
  panelEls().forEach((panel) => {
    out[panel.dataset.panel] = readPanelBox(panel);
  });
  return out;
}

function applyLayout(page) {
  const layout = loadLayout(page);
  panelEls().forEach((panel) => {
    const id = panel.dataset.panel;
    const box = layout[id];
    if (!box) return;
    setPanelBox(panel, box);
  });
}

function workspaceMetrics() {
  const workspace = document.getElementById("workspace");
  const rect = workspace.getBoundingClientRect();
  return {
    rect,
    cellW: rect.width / gridCols,
    cellH: rect.height / gridRows
  };
}

function setupDocking() {
  if (window.matchMedia("(max-width: 1080px)").matches) return;

  panelEls().forEach((panel) => {
    const head = panel.querySelector(".panel-head");
    const handle = panel.querySelector(".resize-handle");
    if (!head || !handle) return;

    head.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button, select, input, label")) return;
      const { rect, cellW, cellH } = workspaceMetrics();
      const box = readPanelBox(panel);
      panel.classList.add("dragging");
      state.dragging = {
        panel,
        box,
        offsetX: event.clientX - rect.left - (box.c - 1) * cellW,
        offsetY: event.clientY - rect.top - (box.r - 1) * cellH
      };
      head.setPointerCapture(event.pointerId);
    });

    handle.addEventListener("pointerdown", (event) => {
      event.stopPropagation();
      const { cellW, cellH } = workspaceMetrics();
      const box = readPanelBox(panel);
      panel.classList.add("resizing");
      state.resizing = {
        panel,
        box,
        startX: event.clientX,
        startY: event.clientY,
        cellW,
        cellH
      };
      handle.setPointerCapture(event.pointerId);
    });
  });

  window.addEventListener("pointermove", (event) => {
    if (state.dragging) {
      const { rect, cellW, cellH } = workspaceMetrics();
      const col = Math.round((event.clientX - rect.left - state.dragging.offsetX) / cellW) + 1;
      const row = Math.round((event.clientY - rect.top - state.dragging.offsetY) / cellH) + 1;
      const box = {
        ...state.dragging.box,
        c: clamp(col, 1, gridCols - state.dragging.box.w + 1),
        r: clamp(row, 1, gridRows - state.dragging.box.h + 1)
      };
      setPanelBox(state.dragging.panel, box);
    }

    if (state.resizing) {
      const dx = event.clientX - state.resizing.startX;
      const dy = event.clientY - state.resizing.startY;
      const dw = Math.round(dx / state.resizing.cellW);
      const dh = Math.round(dy / state.resizing.cellH);
      const box = {
        ...state.resizing.box,
        w: clamp(state.resizing.box.w + dw, 4, gridCols - state.resizing.box.c + 1),
        h: clamp(state.resizing.box.h + dh, 3, gridRows - state.resizing.box.r + 1)
      };
      setPanelBox(state.resizing.panel, box);
    }
  });

  window.addEventListener("pointerup", () => {
    if (state.dragging) {
      state.dragging.panel.classList.remove("dragging");
      state.dragging = null;
      saveLayout(state.page, currentLayout());
    }
    if (state.resizing) {
      state.resizing.panel.classList.remove("resizing");
      state.resizing = null;
      saveLayout(state.page, currentLayout());
    }
  });
}

function renderActivePage(page) {
  state.page = page;
  document.body.dataset.page = page;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });
  const visible = new Set(pagePanels[page] || pagePanels.manual);
  panelEls().forEach((panel) => {
    panel.classList.toggle("panel-hidden", !visible.has(panel.dataset.panel));
  });
  applyLayout(page);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || "Request failed");
  }
  return data;
}

function setBanner(id, text, tone = "muted") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `banner ${tone}`;
}

function updateRangeText() {
  const mt = document.getElementById("maxThrottleValue");
  if (mt) mt.textContent = state.maxThrottle.toFixed(2);
  const sm = document.getElementById("steerMixValue");
  if (sm) sm.textContent = state.steerMix.toFixed(2);
  const sb = document.getElementById("steerBiasValue");
  if (sb) sb.textContent = state.steerBias.toFixed(2);
  const left = document.getElementById("leftMaxSpeed");
  const right = document.getElementById("rightMaxSpeed");
  if (left && document.getElementById("leftMaxSpeedValue")) {
    document.getElementById("leftMaxSpeedValue").textContent = (Number(left.value || 0) / 100).toFixed(2);
  }
  if (right && document.getElementById("rightMaxSpeedValue")) {
    document.getElementById("rightMaxSpeedValue").textContent = (Number(right.value || 0) / 100).toFixed(2);
  }
}

function updateToolbarBadge(status) {
  const badge = document.getElementById("maintenanceBadge");
  if (!badge) return;
  const stopped = !!(status && status.safety_stop);
  badge.textContent = stopped ? "e-stop" : "run";
  badge.classList.toggle("on", stopped);
  badge.classList.toggle("off", !stopped);
}

function setEstopToggle(enabled) {
  state.estopEnabled = !!enabled;
  const btn = document.getElementById("estopToggle");
  if (!btn) return;
  btn.classList.toggle("on", state.estopEnabled);
  btn.classList.toggle("off", !state.estopEnabled);
  btn.setAttribute("aria-pressed", state.estopEnabled ? "true" : "false");
  const title = btn.querySelector(".estop-toggle-title");
  const subtitle = btn.querySelector(".estop-toggle-subtitle");
  if (title) title.textContent = state.estopEnabled ? "E-STOP ACTIVE" : "E-STOP OFF";
  if (subtitle) subtitle.textContent = state.estopEnabled ? "Drive output is locked at zero" : "Tap to engage emergency stop";
}

function setRecordToggle(enabled, pending = false) {
  state.recordEnabled = !!enabled;
  state.recordPending = !!pending;
  const btn = document.getElementById("recordToggleBtn");
  if (!btn) return;
  btn.classList.toggle("on", state.recordEnabled);
  btn.classList.toggle("off", !state.recordEnabled);
  btn.classList.toggle("pending", state.recordPending);
  btn.disabled = state.recordPending;
  btn.setAttribute("aria-pressed", state.recordEnabled ? "true" : "false");
  const title = btn.querySelector(".record-toggle-title");
  const subtitle = btn.querySelector(".record-toggle-subtitle");
  if (title) title.textContent = state.recordEnabled ? "RECORDING ON" : "RECORDING OFF";
  if (subtitle) subtitle.textContent = state.recordPending
    ? (state.recordEnabled ? "Starting capture session…" : "Stopping capture session…")
    : (state.recordEnabled ? "Tap to stop the current capture session" : "Tap to start a capture session");
}

async function sendControlUpdate(extra = {}) {
  const body = {
    steering: state.manualSteering,
    throttle: state.manualThrottle,
    max_throttle: state.maxThrottle,
    steer_mix: state.steerMix,
    steer_bias: state.steerBias,
    current_page: state.page,
    ...extra
  };
  try {
    await fetchJson("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch (error) {
    setBanner("statusBanner", error.message, "muted");
  }
}

function updateStatusUi(data) {
  state.latestStatus = data;
  setEstopToggle(!!data.safety_stop);

  const driveState = data.safety_stop ? "E-stop active" : (data.active_algorithm === "manual" ? "Manual ready" : `${data.active_algorithm || "auto"} active`);
  const previewState = data.camera_preview_live ? "live" : "placeholder";
  const errorText = data.camera_error ? String(data.camera_error) : "none";

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("metricDriveState", driveState);
  setText("metricApplied", `S ${Number(data.applied_steering || 0).toFixed(2)} · T ${Number(data.applied_throttle || 0).toFixed(2)}`);
  setText("metricManual", `S ${Number(state.targetSteering || 0).toFixed(2)} · T ${Number(state.targetThrottle || 0).toFixed(2)}`);
  setText("metricRec", data.recording ? "on" : "off");
  setText("metricPreview", previewState);
  setText("metricCamera", `${data.camera_width || 0}×${data.camera_height || 0} ${data.camera_format || "unknown"}`);
  setText("metricModel", data.active_model || "none");
  setText("metricAlgorithm", data.active_algorithm || "manual");
  setText("metricMaxThrottle", Number(data.max_throttle ?? state.maxThrottle ?? 0).toFixed(2));
  setText("metricSteerMix", Number(data.steer_mix ?? state.steerMix ?? 0).toFixed(2));
  setText("metricSteerBias", Number(data.steer_bias ?? state.steerBias ?? 0).toFixed(2));
  setText("metricWheels", `${Number(data.motor_left || 0).toFixed(2)} / ${Number(data.motor_right || 0).toFixed(2)}`);
  setText("metricFps", `${Number(data.fps || 0).toFixed(1)} FPS`);
  setText("metricBackend", data.camera_backend || "unknown");
  setText("metricError", errorText);

  const previewMeta = document.getElementById("cameraPreviewMeta");
  if (previewMeta) {
    const extraError = data.camera_error ? ` · ${data.camera_error}` : "";
    previewMeta.textContent = `Backend: ${data.camera_backend || "unknown"} · ${previewState} preview${extraError}`;
  }

  setRecordToggle(!!data.recording, false);

  updateToolbarBadge(data);
  setBanner("statusBanner", data.system_message || "Ready.", "muted");
}

async function pollStatus() {
  if (document.hidden) return;
  try {
    const data = await fetchJson("/api/status");
    updateStatusUi(data);
    syncControlsFromStatus(data);
  } catch (error) {
    setBanner("statusBanner", error.message, "muted");
  }
}

async function refreshModels() {
  const data = await fetchJson("/api/model/list");
  const select = document.getElementById("modelSelect");
  if (!select) return;
  select.innerHTML = "";
  (data.models || []).forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    if (data.active === name) option.selected = true;
    select.appendChild(option);
  });
}

async function uploadModel() {
  const input = document.getElementById("modelFile");
  const file = input?.files?.[0];
  if (!file) {
    setBanner("modelMessage", "Choose a .tflite file first.", "muted");
    return;
  }
  const form = new FormData();
  form.append("file", file);
  const data = await fetchJson("/api/model/upload", { method: "POST", body: form });
  setBanner("modelMessage", data.message || "Model uploaded.", "muted");
  await refreshModels();
}

async function loadSelectedModel() {
  const select = document.getElementById("modelSelect");
  const filename = select?.value || "";
  if (!filename) {
    setBanner("modelMessage", "Choose a model first.", "muted");
    return;
  }
  const data = await fetchJson("/api/model/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename })
  });
  setBanner("modelMessage", data.message || "Model loaded.", "muted");
  await pollStatus();
}

async function toggleRecording() {
  const next = !state.recordEnabled;
  setRecordToggle(next, true);
  try {
    const data = await fetchJson("/api/record/toggle", { method: "POST" });
    setBanner("statusBanner", data.message || "Recording toggled.", "muted");
    if (data && data.state) updateStatusUi(data.state);
    else setRecordToggle(!!data.recording, false);
    await pollStatus();
  } catch (error) {
    setRecordToggle(!next, false);
    throw error;
  }
}

async function setEstop(enabled) {
  const data = await fetchJson("/api/system/estop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: !!enabled })
  });
  updateStatusUi(data.state || {});
  if (enabled) {
    setManualTargets(0, 0, { immediateCurrent: true, sendNow: false });
  }
}

function setCameraResolutionPreset() {
  const width = Number(document.getElementById("cameraWidth")?.value || 0);
  const height = Number(document.getElementById("cameraHeight")?.value || 0);
  const preset = document.getElementById("cameraResolutionPreset");
  if (!preset) return;
  const match = `${width}x${height}`;
  const known = Array.from(preset.options).some((opt) => opt.value === match);
  preset.value = known ? match : "custom";
}

function applyCameraResolutionPreset() {
  const preset = document.getElementById("cameraResolutionPreset")?.value;
  if (!preset || preset === "custom") return;
  const [w, h] = preset.split("x").map((v) => Number(v || 0));
  document.getElementById("cameraWidth").value = w;
  document.getElementById("cameraHeight").value = h;
}

function streamQualityPresets() {
  return {
    low_latency: { preview_fps: 10, preview_quality: 40 },
    balanced: { preview_fps: 12, preview_quality: 60 },
    high: { preview_fps: 15, preview_quality: 75 },
    manual: null
  };
}

function applyStreamQualityPreset() {
  const select = document.getElementById("cameraStreamQuality");
  const preset = streamQualityPresets()[select?.value || "manual"];
  if (!preset) return;
  document.getElementById("cameraPreviewFps").value = preset.preview_fps;
  document.getElementById("cameraPreviewQuality").value = preset.preview_quality;
}

function readCameraForm() {
  return {
    width: Number(document.getElementById("cameraWidth").value || 426),
    height: Number(document.getElementById("cameraHeight").value || 240),
    fps: Number(document.getElementById("cameraFps").value || 30),
    preview_fps: Number(document.getElementById("cameraPreviewFps").value || 12),
    preview_quality: Number(document.getElementById("cameraPreviewQuality").value || 60),
    format: document.getElementById("cameraFormat").value || "BGR888",
    stream_quality: document.getElementById("cameraStreamQuality").value || "balanced",
    auto_exposure: !!document.getElementById("cameraAutoExposure").checked,
    awb: !!document.getElementById("cameraAwb").checked,
    exposure_us: Number(document.getElementById("cameraExposureUs").value || 12000),
    analogue_gain: Number(document.getElementById("cameraAnalogueGain").value || 1.0),
    exposure_compensation: Number(document.getElementById("cameraExposureComp").value || 0),
    brightness: Number(document.getElementById("cameraBrightness").value || 0),
    contrast: Number(document.getElementById("cameraContrast").value || 1),
    saturation: Number(document.getElementById("cameraSaturation").value || 1),
    sharpness: Number(document.getElementById("cameraSharpness").value || 1)
  };
}

function fillCameraForm(config = {}) {
  document.getElementById("cameraWidth").value = config.width ?? 426;
  document.getElementById("cameraHeight").value = config.height ?? 240;
  document.getElementById("cameraFps").value = config.fps ?? 30;
  document.getElementById("cameraPreviewFps").value = config.preview_fps ?? 12;
  document.getElementById("cameraPreviewQuality").value = config.preview_quality ?? 60;
  document.getElementById("cameraFormat").value = config.format || "BGR888";
  document.getElementById("cameraStreamQuality").value = config.stream_quality || "balanced";
  document.getElementById("cameraAutoExposure").checked = Boolean(config.auto_exposure ?? true);
  document.getElementById("cameraAwb").checked = Boolean(config.awb ?? true);
  document.getElementById("cameraExposureUs").value = config.exposure_us ?? 12000;
  document.getElementById("cameraAnalogueGain").value = config.analogue_gain ?? 1.0;
  document.getElementById("cameraExposureComp").value = config.exposure_compensation ?? 0;
  document.getElementById("cameraBrightness").value = config.brightness ?? 0;
  document.getElementById("cameraContrast").value = config.contrast ?? 1;
  document.getElementById("cameraSaturation").value = config.saturation ?? 1;
  document.getElementById("cameraSharpness").value = config.sharpness ?? 1;
  setCameraResolutionPreset();
}

async function loadCameraConfig() {
  const data = await fetchJson("/api/camera/config");
  const cfg = data.config || {};
  state.cameraConfig = cfg;
  fillCameraForm(cfg);
  const live = cfg.preview_live ? "Live preview ready." : "Preview is using placeholder.";
  const perf = ` Stream ${cfg.stream_quality || "balanced"}, preview ${cfg.preview_fps ?? 12} FPS @ JPEG ${cfg.preview_quality ?? 60}.`;
  setBanner("cameraMessage", `${live}${perf}`, "muted");
}

async function applyCameraConfig() {
  const payload = readCameraForm();
  const data = await fetchJson("/api/camera/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  state.cameraConfig = data.config || payload;
  setBanner("cameraMessage", data.message || "Camera settings applied.", "muted");
  refreshVideoFeed();
  await pollStatus();
}

function readMotorForm() {
  return {
    left_direction: Number(document.getElementById("leftDirection").value || 1),
    right_direction: Number(document.getElementById("rightDirection").value || 1),
    steering_direction: Number(document.getElementById("steeringDirection").value || 1),
    left_max_speed: Number(document.getElementById("leftMaxSpeed").value || 100) / 100,
    right_max_speed: Number(document.getElementById("rightMaxSpeed").value || 100) / 100,
    left_bias: Number(document.getElementById("leftBias").value || 0),
    right_bias: Number(document.getElementById("rightBias").value || 0)
  };
}

function setMotorFormDirty(dirty = true) {
  state.motorFormDirty = !!dirty;
}

function fillMotorForm(config = {}, force = false) {
  if (state.motorFormDirty && !force) return;
  document.getElementById("leftDirection").value = String(Number(config.left_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById("rightDirection").value = String(Number(config.right_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById("steeringDirection").value = String(Number(config.steering_direction ?? 1) < 0 ? -1 : 1);
  document.getElementById("leftMaxSpeed").value = Math.round(Number(config.left_max_speed ?? 1.0) * 100);
  document.getElementById("rightMaxSpeed").value = Math.round(Number(config.right_max_speed ?? 1.0) * 100);
  document.getElementById("leftBias").value = Number(config.left_bias ?? 0).toFixed(2);
  document.getElementById("rightBias").value = Number(config.right_bias ?? 0).toFixed(2);
  updateRangeText();
  setMotorFormDirty(false);
}

async function loadMotorConfig() {
  const data = await fetchJson("/api/motor/config");
  const cfg = data.config || {};
  state.motorConfig = cfg;
  fillMotorForm(cfg, true);
  setBanner("motorMessage", "Loaded saved motor settings.", "muted");
}

async function applyMotorConfig() {
  const payload = readMotorForm();
  const data = await fetchJson("/api/motor/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  state.motorConfig = data.config || payload;
  fillMotorForm(state.motorConfig, true);
  setBanner("motorMessage", data.message || "Motor settings applied.", "muted");
  await pollStatus();
}

function previewDelayMs() {
  const fps = Number(document.getElementById("cameraPreviewFps")?.value || state.cameraConfig?.preview_fps || 12);
  return clamp(Math.round(1000 / Math.max(1, fps)), 40, 500);
}

async function sendPreviewState(enabled) {
  try {
    await fetchJson("/api/camera/preview_state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !!enabled })
    });
  } catch {
    // keep UI responsive even if preview-state sync fails
  }
}

function stopPreviewLoop(clearImage = false) {
  state.previewActive = false;
  if (state.previewTimer) {
    clearTimeout(state.previewTimer);
    state.previewTimer = null;
  }
  if (clearImage && state.previewObjectUrl) {
    try { URL.revokeObjectURL(state.previewObjectUrl); } catch {}
    state.previewObjectUrl = null;
  }
}

function schedulePreviewFrame(immediate = false) {
  if (!state.previewActive) return;
  if (state.previewTimer) clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(requestPreviewFrame, immediate ? 0 : previewDelayMs());
}

async function requestPreviewFrame() {
  if (!state.previewActive || document.hidden) return;
  if (state.previewInFlight) {
    schedulePreviewFrame(false);
    return;
  }
  state.previewInFlight = true;
  try {
    const response = await fetch(`/api/camera/frame.jpg?t=${Date.now()}`, { cache: "no-store" });
    if (response.status === 204) {
      schedulePreviewFrame(false);
      return;
    }
    if (!response.ok) throw new Error(`Preview request failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const img = document.getElementById("videoFeed");
    const previous = state.previewObjectUrl;
    img.src = url;
    state.previewObjectUrl = url;
    if (previous) {
      try { URL.revokeObjectURL(previous); } catch {}
    }
  } catch {
    // Keep last frame visible.
  } finally {
    state.previewInFlight = false;
    schedulePreviewFrame(false);
  }
}

function refreshVideoFeed() {
  state.previewActive = !document.hidden;
  sendPreviewState(state.previewActive);
  schedulePreviewFrame(true);
}

function syncPreviewActivity() {
  const enabled = !document.hidden;
  state.previewActive = enabled;
  sendPreviewState(enabled);
  if (enabled) schedulePreviewFrame(true);
  else stopPreviewLoop(false);
}

function setManualTargets(steering, throttle, options = {}) {
  state.targetSteering = clamp(Number(steering || 0), -1, 1);
  state.targetThrottle = clamp(Number(throttle || 0), -state.maxThrottle, state.maxThrottle);
  if (options.immediateCurrent) {
    state.manualSteering = state.targetSteering;
    state.manualThrottle = state.targetThrottle;
    applyManualState();
  }
  if (options.sendNow) {
    sendManualState(true);
  }
}

function applyManualState() {
  const dot = document.getElementById("joystickDot");
  const text = document.getElementById("joystickText");
  if (dot) {
    dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
    const throttleRatio = state.maxThrottle > 0 ? state.manualThrottle / state.maxThrottle : 0;
    dot.style.top = `${(0.5 - throttleRatio * 0.5) * 100}%`;
  }
  if (text) {
    text.textContent = `Steering ${state.manualSteering.toFixed(2)} · Throttle ${state.manualThrottle.toFixed(2)} · Target ${state.targetSteering.toFixed(2)} / ${state.targetThrottle.toFixed(2)}`;
  }
}

function updatePointerTarget(clientX, clientY) {
  const area = document.getElementById("joystickArea");
  const rect = area.getBoundingClientRect();
  const nx = clamp((clientX - rect.left) / Math.max(rect.width, 1), 0, 1);
  const ny = clamp((clientY - rect.top) / Math.max(rect.height, 1), 0, 1);
  const steering = (nx - 0.5) * 2;
  const throttle = (0.5 - ny) * 2 * state.maxThrottle;
  setManualTargets(steering, throttle, { sendNow: false });
}

function setStepInput(direction, pressed) {
  if (!(direction in state.stepInputs)) return;
  state.stepInputs[direction] = !!pressed;
}

function processStepInputs() {
  if (state.pointerControl.active || state.estopEnabled) return;
  const horizontal = (state.stepInputs.right ? 1 : 0) - (state.stepInputs.left ? 1 : 0);
  const vertical = (state.stepInputs.up ? 1 : 0) - (state.stepInputs.down ? 1 : 0);

  if (horizontal !== 0) {
    state.targetSteering = clamp(state.targetSteering + horizontal * STEP_SIZE, -1, 1);
  } else {
    state.targetSteering = moveTowards(state.targetSteering, 0, STEP_SIZE);
  }

  if (vertical !== 0) {
    state.targetThrottle = clamp(state.targetThrottle + vertical * STEP_SIZE, -state.maxThrottle, state.maxThrottle);
  } else {
    state.targetThrottle = moveTowards(state.targetThrottle, 0, STEP_SIZE);
  }
}

function sendManualState(force = false) {
  const now = Date.now();
  const changed = !almostEqual(state.manualSteering, state.lastSentSteering, 0.01)
    || !almostEqual(state.manualThrottle, state.lastSentThrottle, 0.01)
    || state.page !== state.lastSentPage;
  if (!force && !changed && now - state.lastControlSentAt < 250) return;
  state.lastSentSteering = state.manualSteering;
  state.lastSentThrottle = state.manualThrottle;
  state.lastSentPage = state.page;
  state.lastControlSentAt = now;
  sendControlUpdate();
}

function controlLoopTick() {
  processStepInputs();

  const nextSteer = moveTowards(state.manualSteering, state.targetSteering, SMOOTH_STEP_STEER);
  const nextThrottle = moveTowards(state.manualThrottle, state.targetThrottle, Math.min(SMOOTH_STEP_THROTTLE, Math.max(state.maxThrottle, SMOOTH_STEP_THROTTLE)));
  const changed = !almostEqual(nextSteer, state.manualSteering, 0.0001) || !almostEqual(nextThrottle, state.manualThrottle, 0.0001);

  if (changed) {
    state.manualSteering = clamp(nextSteer, -1, 1);
    state.manualThrottle = clamp(nextThrottle, -state.maxThrottle, state.maxThrottle);
    applyManualState();
    sendManualState(false);
  }
}

function setupManualControls() {
  const area = document.getElementById("joystickArea");
  applyManualState();
  if (state.stepTimer) clearInterval(state.stepTimer);
  state.stepTimer = setInterval(controlLoopTick, STEP_INTERVAL_MS);

  area.addEventListener("pointerdown", (event) => {
    state.pointerControl.active = true;
    state.pointerControl.id = event.pointerId;
    area.setPointerCapture(event.pointerId);
    updatePointerTarget(event.clientX, event.clientY);
  });

  area.addEventListener("pointermove", (event) => {
    if (!state.pointerControl.active || state.pointerControl.id !== event.pointerId) return;
    updatePointerTarget(event.clientX, event.clientY);
  });

  const releasePointer = (event) => {
    if (state.pointerControl.id !== null && event.pointerId !== undefined && state.pointerControl.id !== event.pointerId) return;
    state.pointerControl.active = false;
    state.pointerControl.id = null;
    setManualTargets(0, 0, { sendNow: false });
  };

  area.addEventListener("pointerup", releasePointer);
  area.addEventListener("pointercancel", releasePointer);
  area.addEventListener("lostpointercapture", releasePointer);


  window.addEventListener("keydown", (event) => {
    if (!(pagePanels[state.page] || []).includes("manual")) return;
    const tag = (event.target?.tagName || "").toLowerCase();
    if (["input", "select", "textarea", "button"].includes(tag)) return;
    const key = String(event.key || "").toLowerCase();
    let handled = true;
    if (key === "w" || key === "arrowup") setStepInput("up", true);
    else if (key === "s" || key === "arrowdown") setStepInput("down", true);
    else if (key === "a" || key === "arrowleft") setStepInput("left", true);
    else if (key === "d" || key === "arrowright") setStepInput("right", true);
    else if (key === " ") setManualTargets(0, 0, { sendNow: false });
    else handled = false;
    if (handled) event.preventDefault();
  });

  window.addEventListener("keyup", (event) => {
    if (!(pagePanels[state.page] || []).includes("manual")) return;
    const key = String(event.key || "").toLowerCase();
    if (key === "w" || key === "arrowup") setStepInput("up", false);
    else if (key === "s" || key === "arrowdown") setStepInput("down", false);
    else if (key === "a" || key === "arrowleft") setStepInput("left", false);
    else if (key === "d" || key === "arrowright") setStepInput("right", false);
  });
}

function setupEvents() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const nextPage = btn.dataset.page;
      if (!nextPage || nextPage === state.page) return;
      renderActivePage(nextPage);
      const extra = { current_page: nextPage };
      if (nextPage === "manual") extra.algorithm = "manual";
      await sendControlUpdate(extra);
      if (nextPage === "camera") await loadCameraConfig();
      if (nextPage === "motor") await loadMotorConfig();
    });
  });

  document.getElementById("saveLayoutBtn").addEventListener("click", () => {
    saveLayout(state.page, currentLayout());
    setBanner("statusBanner", `Saved ${state.page} layout.`, "muted");
  });

  document.getElementById("resetLayoutBtn").addEventListener("click", () => {
    localStorage.removeItem(layoutStorageKey(state.page));
    applyLayout(state.page);
    setBanner("statusBanner", `Reset ${state.page} layout.`, "muted");
  });

  document.getElementById("maxThrottle").addEventListener("input", (event) => {
    state.maxThrottle = Number(event.target.value) / 100;
    state.targetThrottle = clamp(state.targetThrottle, -state.maxThrottle, state.maxThrottle);
    state.manualThrottle = clamp(state.manualThrottle, -state.maxThrottle, state.maxThrottle);
    updateRangeText();
    applyManualState();
    sendControlUpdate();
  });

  document.getElementById("steerMix").addEventListener("input", (event) => {
    state.steerMix = Number(event.target.value) / 100;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("steerBias").addEventListener("input", (event) => {
    state.steerBias = Number(event.target.value) / 100;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("saveRuntimeBtn").addEventListener("click", async () => {
    try {
      const data = await fetchJson("/api/config/save", { method: "POST" });
      setBanner("runtimeMessage", data.message || "Runtime config saved.", "muted");
    } catch (error) {
      setBanner("runtimeMessage", error.message, "muted");
    }
  });

  document.getElementById("recordToggleBtn").addEventListener("click", async () => {
    try {
      await toggleRecording();
    } catch (error) {
      setBanner("statusBanner", error.message, "muted");
    }
  });

  document.getElementById("uploadModelBtn").addEventListener("click", async () => {
    try {
      await uploadModel();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  });

  document.getElementById("refreshModelsBtn").addEventListener("click", refreshModels);
  document.getElementById("loadModelBtn").addEventListener("click", async () => {
    try {
      await loadSelectedModel();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  });

  document.getElementById("estopToggle").addEventListener("click", async () => {
    try {
      await setEstop(!state.estopEnabled);
    } catch (error) {
      setBanner("statusBanner", error.message, "muted");
    }
  });

  document.getElementById("cameraApplyBtn").addEventListener("click", async () => {
    try {
      await applyCameraConfig();
    } catch (error) {
      setBanner("cameraMessage", error.message, "muted");
    }
  });

  document.getElementById("cameraResolutionPreset").addEventListener("change", applyCameraResolutionPreset);
  document.getElementById("cameraStreamQuality").addEventListener("change", applyStreamQualityPreset);
  document.getElementById("cameraWidth").addEventListener("change", setCameraResolutionPreset);
  document.getElementById("cameraHeight").addEventListener("change", setCameraResolutionPreset);

  document.getElementById("motorApplyBtn").addEventListener("click", async () => {
    try {
      await applyMotorConfig();
    } catch (error) {
      setBanner("motorMessage", error.message, "muted");
    }
  });

  ["leftDirection", "rightDirection", "steeringDirection", "leftMaxSpeed", "rightMaxSpeed", "leftBias", "rightBias"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", () => setMotorFormDirty(true));
    el.addEventListener("change", () => setMotorFormDirty(true));
  });
  document.getElementById("leftMaxSpeed").addEventListener("input", updateRangeText);
  document.getElementById("rightMaxSpeed").addEventListener("input", updateRangeText);
}

function syncControlsFromStatus(data) {
  if (!data || typeof data !== "object") return;
  state.maxThrottle = Number(data.max_throttle ?? state.maxThrottle ?? 0.55);
  state.steerMix = Number(data.steer_mix ?? state.steerMix ?? 0.5);
  state.steerBias = Number(data.steer_bias ?? state.steerBias ?? 0);
  const maxThrottleEl = document.getElementById("maxThrottle");
  const steerMixEl = document.getElementById("steerMix");
  const steerBiasEl = document.getElementById("steerBias");
  if (maxThrottleEl) maxThrottleEl.value = Math.round(state.maxThrottle * 100);
  if (steerMixEl) steerMixEl.value = Math.round(state.steerMix * 100);
  if (steerBiasEl) steerBiasEl.value = Math.round(state.steerBias * 100);

  const allowMotorFormSync = !(state.page === "motor" && state.motorFormDirty);
  if (allowMotorFormSync && typeof data.motor_left_max_speed === "number") {
    fillMotorForm({
      left_direction: data.motor_left_direction,
      right_direction: data.motor_right_direction,
      steering_direction: data.motor_steering_direction,
      left_max_speed: data.motor_left_max_speed,
      right_max_speed: data.motor_right_max_speed,
      left_bias: data.motor_left_bias,
      right_bias: data.motor_right_bias
    });
  }

  updateRangeText();
  const desiredPage = data.current_page || state.page || "manual";
  if (desiredPage !== state.page && defaultLayouts[desiredPage]) {
    renderActivePage(desiredPage);
  }
}

async function init() {
  renderActivePage(state.page);
  updateRangeText();
  setupDocking();
  setupManualControls();
  setupEvents();
  await refreshModels();
  await loadCameraConfig();
  await loadMotorConfig();
  syncPreviewActivity();
  document.addEventListener("visibilitychange", syncPreviewActivity);
  window.addEventListener("beforeunload", () => {
    sendPreviewState(false);
    stopPreviewLoop(false);
    if (state.stepTimer) clearInterval(state.stepTimer);
  });
  const status = await fetchJson("/api/status");
  updateStatusUi(status);
  syncControlsFromStatus(status);
  applyManualState();
  state.statusTimer = setInterval(pollStatus, 800);
}

window.addEventListener("load", init);
