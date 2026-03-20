const gridCols = 24;
const gridRows = 14;
const layoutKeyPrefix = "PiServerLayout:";
const controlStep = 0.1;
const controlStepMs = 100;

const pagePanels = {
  manual: ["status", "viewer", "runtime", "manual", "record"],
  training: ["status", "viewer", "runtime", "model", "record"],
  auto: ["status", "viewer", "runtime", "model"],
  camera: ["status", "viewer", "camera"],
  motor: ["status", "viewer", "motor"]
};

const defaultLayouts = {
  manual: {
    status: { c: 1, r: 1, w: 24, h: 3 },
    viewer: { c: 1, r: 4, w: 14, h: 9 },
    runtime: { c: 15, r: 4, w: 10, h: 4 },
    manual: { c: 15, r: 8, w: 10, h: 5 },
    record: { c: 1, r: 13, w: 24, h: 2 }
  },
  training: {
    status: { c: 1, r: 1, w: 24, h: 3 },
    viewer: { c: 1, r: 4, w: 14, h: 9 },
    runtime: { c: 15, r: 4, w: 10, h: 4 },
    model: { c: 15, r: 8, w: 10, h: 5 },
    record: { c: 1, r: 13, w: 24, h: 2 }
  },
  auto: {
    status: { c: 1, r: 1, w: 24, h: 3 },
    viewer: { c: 1, r: 4, w: 15, h: 11 },
    runtime: { c: 16, r: 4, w: 9, h: 4 },
    model: { c: 16, r: 8, w: 9, h: 7 }
  },
  camera: {
    status: { c: 1, r: 1, w: 24, h: 3 },
    viewer: { c: 1, r: 4, w: 13, h: 11 },
    camera: { c: 14, r: 4, w: 11, h: 11 }
  },
  motor: {
    status: { c: 1, r: 1, w: 24, h: 3 },
    viewer: { c: 1, r: 4, w: 13, h: 11 },
    motor: { c: 14, r: 4, w: 11, h: 11 }
  }
};

const state = {
  page: "manual",
  manualSteering: 0,
  manualThrottle: 0,
  maxThrottle: 0.55,
  steerMix: 0.5,
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
  availableAlgorithms: [],
  stepTimer: null,
  controlIntent: { up: false, down: false, left: false, right: false }
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function roundStep(value) {
  return Math.round(value * 100) / 100;
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

function applyLayout(page) {
  const layout = loadLayout(page);
  panelEls().forEach((panel) => {
    const id = panel.dataset.panel;
    const box = layout[id];
    if (!box) return;
    panel.style.setProperty("--c", box.c);
    panel.style.setProperty("--r", box.r);
    panel.style.setProperty("--w", box.w);
    panel.style.setProperty("--h", box.h);
  });
}

function currentLayout() {
  const out = {};
  panelEls().forEach((panel) => {
    out[panel.dataset.panel] = readPanelBox(panel);
  });
  return out;
}

function readPanelBox(panel) {
  const style = getComputedStyle(panel);
  return {
    c: Number(style.getPropertyValue("--c")) || 1,
    r: Number(style.getPropertyValue("--r")) || 1,
    w: Number(style.getPropertyValue("--w")) || 6,
    h: Number(style.getPropertyValue("--h")) || 3
  };
}

function setPanelBox(panel, box) {
  panel.style.setProperty("--c", box.c);
  panel.style.setProperty("--r", box.r);
  panel.style.setProperty("--w", box.w);
  panel.style.setProperty("--h", box.h);
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
  if (window.matchMedia("(max-width: 960px)").matches) return;

  panelEls().forEach((panel) => {
    const head = panel.querySelector(".panel-head");
    const handle = panel.querySelector(".resize-handle");

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
      const { rect, cellW, cellH } = workspaceMetrics();
      const box = readPanelBox(panel);
      panel.classList.add("resizing");
      state.resizing = {
        panel,
        box,
        startX: event.clientX,
        startY: event.clientY,
        cellW,
        cellH,
        rect
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
        w: clamp(state.resizing.box.w + dw, 3, gridCols - state.resizing.box.c + 1),
        h: clamp(state.resizing.box.h + dh, 2, gridRows - state.resizing.box.r + 1)
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
  const maxThrottleValue = document.getElementById("maxThrottleValue");
  const steerMixValue = document.getElementById("steerMixValue");
  if (maxThrottleValue) maxThrottleValue.textContent = state.maxThrottle.toFixed(2);
  if (steerMixValue) steerMixValue.textContent = state.steerMix.toFixed(2);
  const left = document.getElementById("leftMaxSpeed");
  const right = document.getElementById("rightMaxSpeed");
  if (left) document.getElementById("leftMaxSpeedValue").textContent = (Number(left.value || 0) / 100).toFixed(2);
  if (right) document.getElementById("rightMaxSpeedValue").textContent = (Number(right.value || 0) / 100).toFixed(2);
}

function updateToolbarBadge(status) {
  const badge = document.getElementById("maintenanceBadge");
  if (!badge) return;
  const stopped = !!(status && status.safety_stop);
  badge.textContent = stopped ? "stop" : "run";
  badge.classList.toggle("on", stopped);
  badge.classList.toggle("off", !stopped);
}

function motorMapText(data) {
  const leftDir = Number(data.motor_left_direction || 1) < 0 ? "R" : "N";
  const rightDir = Number(data.motor_right_direction || 1) < 0 ? "R" : "N";
  const steerDir = Number(data.motor_steering_direction || 1) < 0 ? "R" : "N";
  return `${leftDir} / ${rightDir} · steer ${steerDir}`;
}

function driveStateText(data) {
  if (data.safety_stop) return "e-stop active";
  const algo = String(data.active_algorithm || "manual");
  if (algo === "manual") return "manual ready";
  return `${algo} live`;
}

function previewStateText(data) {
  return data.camera_preview_live ? "live" : "placeholder";
}

function setEstopUi(enabled) {
  const toggle = document.getElementById("estopToggle");
  const label = document.getElementById("estopToggleLabel");
  const hint = document.getElementById("estopToggleHint");
  const wrapper = toggle ? toggle.closest(".estop-toggle") : null;
  if (toggle) toggle.checked = !!enabled;
  if (wrapper) wrapper.classList.toggle("is-active", !!enabled);
  if (label) label.textContent = enabled ? "E-Stop active" : "E-Stop off";
  if (hint) hint.textContent = enabled ? "Safety lock engaged" : "Motion enabled";
}

async function sendControlUpdate(extra = {}) {
  const body = {
    steering: state.manualSteering,
    throttle: state.manualThrottle,
    max_throttle: state.maxThrottle,
    steer_mix: state.steerMix,
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
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText("metricPage", data.current_page || state.page || "manual");
  setText("metricDriveState", driveStateText(data));
  setText("metricAlgorithm", data.active_algorithm || "manual");
  setText("metricModel", data.active_model || "none");
  setText("metricFps", Number(data.fps || 0).toFixed(1));
  setText("metricRec", data.recording ? "on" : "off");
  setText("metricCamera", `${data.camera_width || 0}×${data.camera_height || 0} ${data.camera_format || "unknown"}`);
  setText("metricPreview", previewStateText(data));
  setText("metricApplied", `S ${Number(data.applied_steering || 0).toFixed(2)} · T ${Number(data.applied_throttle || 0).toFixed(2)}`);
  setText("metricManual", `S ${Number(data.manual_steering || 0).toFixed(2)} · T ${Number(data.manual_throttle || 0).toFixed(2)}`);
  setText("metricMaxThrottle", Number(data.max_throttle || 0).toFixed(2));
  setText("metricSteerMix", Number(data.steer_mix || 0).toFixed(2));
  setText("metricWheels", `${Number(data.motor_left || 0).toFixed(2)} / ${Number(data.motor_right || 0).toFixed(2)}`);
  setText("metricMotorMap", motorMapText(data));

  const previewMeta = document.getElementById("cameraPreviewMeta");
  if (previewMeta) {
    const liveText = data.camera_preview_live ? "live preview" : "placeholder preview";
    const errorText = data.camera_error ? ` · ${data.camera_error}` : "";
    previewMeta.textContent = `Backend: ${data.camera_backend || "unknown"} · ${liveText}${errorText}`;
  }

  const recBadge = document.getElementById("recordStateBadge");
  if (recBadge) {
    recBadge.textContent = data.recording ? "on" : "off";
    recBadge.classList.toggle("on", !!data.recording);
    recBadge.classList.toggle("off", !data.recording);
  }

  updateToolbarBadge(data);
  setEstopUi(!!data.safety_stop);
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

async function refreshAlgorithms() {
  const data = await fetchJson("/api/algorithms");
  state.availableAlgorithms = Array.isArray(data.algorithms) ? data.algorithms.map((algo) => algo.name) : [];
  return state.availableAlgorithms;
}

function desiredAlgorithmForPage(page) {
  const algos = state.availableAlgorithms || [];
  if (page === "auto") {
    if (algos.includes("autopilot")) return "autopilot";
    if (algos.includes("auto_steer")) return "auto_steer";
    if (algos.includes("manual")) return "manual";
  }
  if (algos.includes("manual")) return "manual";
  return null;
}

async function refreshModels() {
  const data = await fetchJson("/api/model/list");
  const select = document.getElementById("modelSelect");
  if (!select) return;
  select.innerHTML = "";
  data.models.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    option.selected = name === data.active;
    select.appendChild(option);
  });
  setBanner("modelMessage", data.active ? `Active model: ${data.active}` : "No active model.", "muted");
}

async function uploadModel() {
  const input = document.getElementById("modelFile");
  if (!input.files || !input.files.length) {
    setBanner("modelMessage", "Choose a .tflite file first.", "muted");
    return;
  }

  const formData = new FormData();
  formData.append("file", input.files[0]);
  const data = await fetchJson("/api/model/upload", {
    method: "POST",
    body: formData
  });
  input.value = "";
  await refreshModels();
  setBanner("modelMessage", data.message || "Model uploaded.", "muted");
}

async function loadSelectedModel() {
  const select = document.getElementById("modelSelect");
  const filename = select ? select.value : "";
  if (!filename) {
    setBanner("modelMessage", "No model selected.", "muted");
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
  const data = await fetchJson("/api/record/toggle", { method: "POST" });
  updateStatusUi(data.state || state.latestStatus || {});
  setBanner("statusBanner", data.message || "Recording toggled.", "muted");
}

async function setEstop(enabled) {
  const data = await fetchJson("/api/system/estop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled })
  });
  updateStatusUi(data.state || state.latestStatus || {});
  syncControlsFromStatus(data.state || state.latestStatus || {});
}

function setCameraResolutionPreset() {
  const preset = document.getElementById("cameraResolutionPreset");
  if (!preset) return;
  const width = Number(document.getElementById("cameraWidth").value || 0);
  const height = Number(document.getElementById("cameraHeight").value || 0);
  const value = `${width}x${height}`;
  const known = Array.from(preset.options).some((opt) => opt.value === value);
  preset.value = known ? value : "custom";
}

function applyCameraResolutionPreset() {
  const preset = document.getElementById("cameraResolutionPreset");
  if (!preset || !preset.value || preset.value === "custom") return;
  const [width, height] = preset.value.split("x").map((v) => Number(v));
  if (width > 0) document.getElementById("cameraWidth").value = width;
  if (height > 0) document.getElementById("cameraHeight").value = height;
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
  if (!select) return;
  const preset = streamQualityPresets()[select.value];
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
    stream_quality: document.getElementById("cameraStreamQuality").value || "balanced",
    format: document.getElementById("cameraFormat").value || "BGR888",
    auto_exposure: document.getElementById("cameraAutoExposure").checked,
    exposure_us: Number(document.getElementById("cameraExposureUs").value || 12000),
    analogue_gain: Number(document.getElementById("cameraAnalogueGain").value || 1.0),
    exposure_compensation: Number(document.getElementById("cameraExposureComp").value || 0.0),
    auto_white_balance: document.getElementById("cameraAwb").checked,
    brightness: Number(document.getElementById("cameraBrightness").value || 0.0),
    contrast: Number(document.getElementById("cameraContrast").value || 1.0),
    saturation: Number(document.getElementById("cameraSaturation").value || 1.0),
    sharpness: Number(document.getElementById("cameraSharpness").value || 1.0)
  };
}

function fillCameraForm(config = {}) {
  state.cameraConfig = config;
  document.getElementById("cameraWidth").value = config.width ?? 426;
  document.getElementById("cameraHeight").value = config.height ?? 240;
  document.getElementById("cameraFps").value = config.fps ?? 30;
  document.getElementById("cameraPreviewFps").value = config.preview_fps ?? 12;
  document.getElementById("cameraPreviewQuality").value = config.preview_quality ?? 60;
  document.getElementById("cameraStreamQuality").value = config.stream_quality || "balanced";
  document.getElementById("cameraFormat").value = config.format || "BGR888";
  document.getElementById("cameraAutoExposure").checked = Boolean(config.auto_exposure ?? true);
  document.getElementById("cameraExposureUs").value = config.exposure_us ?? 12000;
  document.getElementById("cameraAnalogueGain").value = config.analogue_gain ?? 1.0;
  document.getElementById("cameraExposureComp").value = config.exposure_compensation ?? 0.0;
  document.getElementById("cameraAwb").checked = Boolean(config.auto_white_balance ?? true);
  document.getElementById("cameraBrightness").value = config.brightness ?? 0.0;
  document.getElementById("cameraContrast").value = config.contrast ?? 1.0;
  document.getElementById("cameraSaturation").value = config.saturation ?? 1.0;
  document.getElementById("cameraSharpness").value = config.sharpness ?? 1.0;
  setCameraResolutionPreset();
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
  state.motorFormDirty = Boolean(dirty);
  if (state.motorFormDirty) {
    setBanner("motorMessage", "Unsaved motor changes. Click Apply motor settings to save and use them.", "muted");
  }
}

function fillMotorForm(config = {}, force = false) {
  if (!force && state.page === "motor" && state.motorFormDirty) return;
  state.motorConfig = config;
  document.getElementById("leftDirection").value = String(config.left_direction ?? 1);
  document.getElementById("rightDirection").value = String(config.right_direction ?? 1);
  document.getElementById("steeringDirection").value = String(config.steering_direction ?? 1);
  document.getElementById("leftMaxSpeed").value = Math.round(Number(config.left_max_speed ?? 1.0) * 100);
  document.getElementById("rightMaxSpeed").value = Math.round(Number(config.right_max_speed ?? 1.0) * 100);
  document.getElementById("leftBias").value = Number(config.left_bias ?? 0).toFixed(2);
  document.getElementById("rightBias").value = Number(config.right_bias ?? 0).toFixed(2);
  state.motorFormDirty = false;
  updateRangeText();
}

async function loadMotorConfig() {
  const data = await fetchJson("/api/motor/config");
  fillMotorForm(data.config || {}, true);
  const cfg = data.config || {};
  const steerMode = Number(cfg.steering_direction || 1) < 0 ? "reversed" : "normal";
  setBanner(
    "motorMessage",
    `Saved motor settings loaded. Left ${Number(cfg.left_direction || 1) < 0 ? "reverse" : "normal"}, right ${Number(cfg.right_direction || 1) < 0 ? "reverse" : "normal"}, steering ${steerMode}.`,
    "muted"
  );
}

async function applyMotorConfig() {
  const payload = readMotorForm();
  const data = await fetchJson("/api/motor/apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  fillMotorForm(data.config || payload, true);
  setBanner("motorMessage", data.message || "Motor settings applied.", "muted");
  await pollStatus();
}

function previewDelayMs() {
  const fps = Number(document.getElementById("cameraPreviewFps")?.value || state.cameraConfig?.preview_fps || 12);
  return Math.max(40, Math.round(1000 / Math.max(1, fps)));
}

async function sendPreviewState(enabled) {
  try {
    await fetchJson("/api/camera/preview_state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled })
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
    if (response.status === 204) return;
    if (!response.ok) throw new Error(`Preview request failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const img = document.getElementById("videoFeed");
    const previous = state.previewObjectUrl;
    if (img) img.src = url;
    state.previewObjectUrl = url;
    if (previous) {
      try { URL.revokeObjectURL(previous); } catch {}
    }
  } catch (error) {
    const msg = error && error.message ? error.message : "Preview update failed.";
    setBanner("cameraMessage", msg, "muted");
  } finally {
    state.previewInFlight = false;
    schedulePreviewFrame(false);
  }
}

function forceRefreshVideoFeed() {
  stopPreviewLoop(true);
  const img = document.getElementById("videoFeed");
  if (img) img.src = "";
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

async function loadCameraConfig() {
  const data = await fetchJson("/api/camera/config");
  fillCameraForm(data.config || {});
  const cfg = data.config || {};
  const backend = cfg.backend ? ` Backend: ${cfg.backend}.` : "";
  const live = cfg.preview_live ? " Live preview ready." : " Preview is using placeholder.";
  const perf = ` Stream ${cfg.stream_quality || "balanced"}, preview ${cfg.preview_fps ?? 12} FPS @ JPEG ${cfg.preview_quality ?? 60}.`;
  const extra = cfg.processing_enabled ? " AI/recording path active." : " AI/recording path idle.";
  const error = cfg.last_error ? ` ${cfg.last_error}` : "";
  setBanner("cameraMessage", `Saved camera settings loaded.${backend}${live}${perf}${extra}${error}`.trim(), "muted");
}

async function applyCameraConfig() {
  const payload = readCameraForm();
  const button = document.getElementById("cameraApplyBtn");
  if (button) button.disabled = true;
  try {
    stopPreviewLoop(true);
    await sendPreviewState(false);
    const data = await fetchJson("/api/camera/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    fillCameraForm(data.config || payload);
    await new Promise((resolve) => setTimeout(resolve, 350));
    await loadCameraConfig();
    forceRefreshVideoFeed();
    await new Promise((resolve) => setTimeout(resolve, 250));
    forceRefreshVideoFeed();
    await pollStatus();
    setBanner("cameraMessage", data.message || "Camera restarted and settings saved.", data.ok ? "muted" : "warn");
  } finally {
    if (button) button.disabled = false;
  }
}

function updateManualVisuals() {
  const dot = document.getElementById("joystickDot");
  const text = document.getElementById("joystickText");
  if (dot) {
    dot.style.left = `${(state.manualSteering * 0.5 + 0.5) * 100}%`;
    dot.style.top = `${(0.5 - (state.manualThrottle / Math.max(state.maxThrottle || 1, 0.01)) / 2.0) * 100}%`;
    dot.style.transform = "translate(-50%, -50%)";
  }
  if (text) {
    text.textContent = `Steering ${state.manualSteering.toFixed(2)} · Throttle ${state.manualThrottle.toFixed(2)}`;
  }
}

function applyManualState() {
  updateManualVisuals();
  sendControlUpdate();
}

function resetManualState(immediate = true) {
  state.controlIntent = { up: false, down: false, left: false, right: false };
  updateArrowButtonState();
  if (immediate) {
    state.manualSteering = 0;
    state.manualThrottle = 0;
    applyManualState();
  }
}

function stepAxis(value, positive, negative, maxAbs) {
  if (positive && !negative) {
    return clamp(roundStep(value + controlStep), -maxAbs, maxAbs);
  }
  if (negative && !positive) {
    return clamp(roundStep(value - controlStep), -maxAbs, maxAbs);
  }
  if (Math.abs(value) <= controlStep) return 0;
  return roundStep(value + (value > 0 ? -controlStep : controlStep));
}

function updateArrowButtonState() {
  const bindings = [
    ["upBtn", state.controlIntent.up],
    ["downBtn", state.controlIntent.down],
    ["leftBtn", state.controlIntent.left],
    ["rightBtn", state.controlIntent.right]
  ];
  bindings.forEach(([id, active]) => {
    const btn = document.getElementById(id);
    if (btn) btn.classList.toggle("is-held", !!active);
  });
}

function stepManualIntent() {
  if (state.page !== "manual") {
    return;
  }
  const nextThrottle = stepAxis(state.manualThrottle, state.controlIntent.up, state.controlIntent.down, state.maxThrottle);
  const nextSteering = stepAxis(state.manualSteering, state.controlIntent.right, state.controlIntent.left, 1);
  if (nextThrottle !== state.manualThrottle || nextSteering !== state.manualSteering) {
    state.manualThrottle = nextThrottle;
    state.manualSteering = nextSteering;
    applyManualState();
  }
}

function startManualStepLoop() {
  if (state.stepTimer) clearInterval(state.stepTimer);
  state.stepTimer = setInterval(stepManualIntent, controlStepMs);
}

function setControlIntent(direction, pressed) {
  if (!(direction in state.controlIntent)) return;
  state.controlIntent[direction] = pressed;
  updateArrowButtonState();
}

function setupJoystick() {
  const area = document.getElementById("joystickArea");
  const centerBtn = document.getElementById("centerBtn");
  if (!area) return;

  function moveDot(clientX, clientY) {
    const rect = area.getBoundingClientRect();
    const x = clamp((clientX - rect.left) / rect.width, 0, 1);
    const y = clamp((clientY - rect.top) / rect.height, 0, 1);

    const centeredX = (x - 0.5) * 2.0;
    const centeredY = (0.5 - y) * 2.0;

    state.manualSteering = clamp(roundStep(centeredX), -1, 1);
    state.manualThrottle = clamp(roundStep(centeredY * state.maxThrottle), -state.maxThrottle, state.maxThrottle);
    applyManualState();
  }

  function resetDot() {
    state.manualSteering = 0;
    state.manualThrottle = 0;
    applyManualState();
  }

  area.addEventListener("pointerdown", (event) => {
    area.setPointerCapture(event.pointerId);
    moveDot(event.clientX, event.clientY);
  });
  area.addEventListener("pointermove", (event) => {
    if (event.buttons) moveDot(event.clientX, event.clientY);
  });
  area.addEventListener("pointerup", resetDot);
  area.addEventListener("pointercancel", resetDot);
  updateManualVisuals();

  [["upBtn", "up"], ["downBtn", "down"], ["leftBtn", "left"], ["rightBtn", "right"]].forEach(([id, direction]) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    const setPressed = (pressed) => {
      if (state.page !== "manual") return;
      setControlIntent(direction, pressed);
    };
    btn.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      btn.setPointerCapture(event.pointerId);
      setPressed(true);
    });
    btn.addEventListener("pointerup", () => setPressed(false));
    btn.addEventListener("pointercancel", () => setPressed(false));
    btn.addEventListener("pointerleave", () => setPressed(false));
  });

  if (centerBtn) {
    centerBtn.addEventListener("click", () => {
      state.manualSteering = 0;
      state.manualThrottle = 0;
      applyManualState();
    });
  }

  const handleKeyChange = (event, pressed) => {
    const tag = (event.target && event.target.tagName) ? event.target.tagName.toLowerCase() : "";
    if (["input", "select", "textarea", "button"].includes(tag)) return;
    const key = String(event.key || "").toLowerCase();
    const mapping = {
      w: "up",
      arrowup: "up",
      s: "down",
      arrowdown: "down",
      a: "left",
      arrowleft: "left",
      d: "right",
      arrowright: "right"
    };
    const direction = mapping[key];
    if (!direction || state.page !== "manual") return;
    event.preventDefault();
    setControlIntent(direction, pressed);
  };

  window.addEventListener("keydown", (event) => handleKeyChange(event, true));
  window.addEventListener("keyup", (event) => handleKeyChange(event, false));
}

async function switchToPage(nextPage) {
  if (!nextPage || nextPage === state.page) return;
  const leavingManual = state.page === "manual" && nextPage !== "manual";
  if (leavingManual) {
    resetManualState(true);
  }
  renderActivePage(nextPage);
  const extra = { current_page: nextPage };
  const desiredAlgorithm = desiredAlgorithmForPage(nextPage);
  if (desiredAlgorithm) extra.algorithm = desiredAlgorithm;
  await sendControlUpdate(extra);
  if (nextPage === "camera") {
    try {
      forceRefreshVideoFeed();
      await loadCameraConfig();
    } catch (error) {
      setBanner("cameraMessage", error.message, "muted");
    }
  }
  if (nextPage === "motor") {
    try {
      await loadMotorConfig();
    } catch (error) {
      setBanner("motorMessage", error.message, "muted");
    }
  }
  if (nextPage === "auto" || nextPage === "training") {
    try {
      await refreshModels();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  }
}

function setupEvents() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await switchToPage(btn.dataset.page);
      } catch (error) {
        setBanner("statusBanner", error.message, "muted");
      }
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
    updateRangeText();
    updateManualVisuals();
    sendControlUpdate();
  });

  document.getElementById("steerMix").addEventListener("input", (event) => {
    state.steerMix = Number(event.target.value) / 100;
    updateRangeText();
    sendControlUpdate();
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

  document.getElementById("refreshModelsBtn").addEventListener("click", async () => {
    try {
      await refreshModels();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  });

  document.getElementById("loadModelBtn").addEventListener("click", async () => {
    try {
      await loadSelectedModel();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
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

  const estopToggle = document.getElementById("estopToggle");
  if (estopToggle) {
    estopToggle.addEventListener("change", async (event) => {
      try {
        await setEstop(event.target.checked);
      } catch (error) {
        setBanner("statusBanner", error.message, "muted");
        setEstopUi(Boolean(state.latestStatus && state.latestStatus.safety_stop));
      }
    });
  }
}

function syncControlsFromStatus(data) {
  if (!data || typeof data !== "object") return;
  state.maxThrottle = Number(data.max_throttle || 0.55);
  state.steerMix = Number(data.steer_mix || 0.5);
  const maxThrottle = document.getElementById("maxThrottle");
  const steerMix = document.getElementById("steerMix");
  if (maxThrottle) maxThrottle.value = Math.round(state.maxThrottle * 100);
  if (steerMix) steerMix.value = Math.round(state.steerMix * 100);

  const allowMotorFormSync = !(state.page === "motor" && state.motorFormDirty);
  if (typeof data.motor_left_max_speed === "number" && allowMotorFormSync) {
    const left = document.getElementById("leftMaxSpeed");
    const right = document.getElementById("rightMaxSpeed");
    if (left) left.value = Math.round(Number(data.motor_left_max_speed || 1) * 100);
    if (right) right.value = Math.round(Number(data.motor_right_max_speed || 1) * 100);
    document.getElementById("leftDirection").value = String(Number(data.motor_left_direction || 1) < 0 ? -1 : 1);
    document.getElementById("rightDirection").value = String(Number(data.motor_right_direction || 1) < 0 ? -1 : 1);
    document.getElementById("steeringDirection").value = String(Number(data.motor_steering_direction || 1) < 0 ? -1 : 1);
    document.getElementById("leftBias").value = Number(data.motor_left_bias || 0).toFixed(2);
    document.getElementById("rightBias").value = Number(data.motor_right_bias || 0).toFixed(2);
  }

  updateRangeText();
  updateManualVisuals();

  const desiredPage = data.current_page || state.page || "manual";
  if (desiredPage !== state.page && defaultLayouts[desiredPage]) {
    renderActivePage(desiredPage);
  }
}

async function init() {
  renderActivePage(state.page);
  updateRangeText();
  updateManualVisuals();
  setupDocking();
  setupJoystick();
  setupEvents();
  startManualStepLoop();
  await refreshAlgorithms();
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
  state.statusTimer = setInterval(pollStatus, 800);
}

window.addEventListener("load", init);
