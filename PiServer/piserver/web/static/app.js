const gridCols = 24;
const gridRows = 14;
const layoutKeyPrefix = "PiServerLayout:";
const defaultLayouts = {
  manual: {
    status: { c: 1, r: 1, w: 10, h: 2 },
    viewer: { c: 1, r: 3, w: 15, h: 10 },
    drive: { c: 16, r: 1, w: 9, h: 5 },
    manual: { c: 16, r: 6, w: 9, h: 5 },
    record: { c: 1, r: 13, w: 8, h: 2 },
    system: { c: 9, r: 13, w: 16, h: 2 },
    camera: { c: 16, r: 1, w: 9, h: 5 }
  },
  training: {
    status: { c: 1, r: 1, w: 8, h: 2 },
    viewer: { c: 1, r: 3, w: 14, h: 9 },
    drive: { c: 15, r: 1, w: 10, h: 6 },
    manual: { c: 15, r: 7, w: 10, h: 5 },
    record: { c: 1, r: 12, w: 8, h: 3 },
    system: { c: 9, r: 12, w: 16, h: 3 },
    camera: { c: 15, r: 1, w: 10, h: 6 }
  },
  auto: {
    status: { c: 1, r: 1, w: 7, h: 2 },
    viewer: { c: 1, r: 3, w: 16, h: 10 },
    drive: { c: 17, r: 1, w: 8, h: 6 },
    manual: { c: 17, r: 7, w: 8, h: 4 },
    record: { c: 1, r: 13, w: 7, h: 2 },
    system: { c: 8, r: 13, w: 17, h: 2 },
    camera: { c: 17, r: 1, w: 8, h: 6 }
  },
  camera: {
    status: { c: 1, r: 1, w: 8, h: 2 },
    viewer: { c: 1, r: 3, w: 15, h: 10 },
    camera: { c: 16, r: 1, w: 9, h: 12 },
    system: { c: 1, r: 13, w: 15, h: 2 },
    drive: { c: 16, r: 1, w: 9, h: 6 },
    manual: { c: 16, r: 7, w: 9, h: 4 },
    record: { c: 16, r: 11, w: 9, h: 2 }
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
  cameraConfig: null
};

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
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
  document.getElementById("maxThrottleValue").textContent = state.maxThrottle.toFixed(2);
  document.getElementById("steerMixValue").textContent = state.steerMix.toFixed(2);
  document.getElementById("manualSpeedValue").textContent = state.maxThrottle.toFixed(2);
}

function updateToolbarBadge(status) {
  const badge = document.getElementById("maintenanceBadge");
  if (!badge) return;
  const stopped = !!(status && status.safety_stop);
  badge.textContent = stopped ? "stop" : "run";
  badge.classList.toggle("on", stopped);
  badge.classList.toggle("off", !stopped);
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
  document.getElementById("metricAlgorithm").textContent = data.active_algorithm || "manual";
  document.getElementById("metricModel").textContent = data.active_model || "none";
  document.getElementById("metricFps").textContent = Number(data.fps || 0).toFixed(1);
  document.getElementById("metricRec").textContent = data.recording ? "on" : "off";
  document.getElementById("metricWheels").textContent = `${Number(data.motor_left || 0).toFixed(2)} / ${Number(data.motor_right || 0).toFixed(2)}`;
  document.getElementById("metricCamera").textContent = `${data.camera_width || 0}×${data.camera_height || 0} ${data.camera_format || "unknown"}`;

  const previewMeta = document.getElementById("cameraPreviewMeta");
  if (previewMeta) {
    const liveText = data.camera_preview_live ? "live preview" : "placeholder preview";
    const errorText = data.camera_error ? ` · ${data.camera_error}` : "";
    previewMeta.textContent = `Backend: ${data.camera_backend || "unknown"} · ${liveText}${errorText}`;
  }

  const recBadge = document.getElementById("recordStateBadge");
  recBadge.textContent = data.recording ? "on" : "off";
  recBadge.classList.toggle("on", !!data.recording);
  recBadge.classList.toggle("off", !data.recording);

  updateToolbarBadge(data);
  setBanner("statusBanner", data.system_message || "Ready.", "muted");
}

async function pollStatus() {
  try {
    const data = await fetchJson("/api/status");
    updateStatusUi(data);
    syncControlsFromStatus(data);
  } catch (error) {
    setBanner("systemMessage", error.message, "muted");
  }
}

async function refreshAlgorithms() {
  const data = await fetchJson("/api/algorithms");
  const select = document.getElementById("algorithmSelect");
  select.innerHTML = "";
  data.algorithms.forEach((algo) => {
    const option = document.createElement("option");
    option.value = algo.name;
    option.textContent = algo.label || algo.name;
    select.appendChild(option);
  });
}

async function refreshModels() {
  const data = await fetchJson("/api/model/list");
  const select = document.getElementById("modelSelect");
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
  const filename = select.value;
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
  setBanner("systemMessage", data.message || "Recording toggled.", "muted");
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

async function runSystemAction(endpoint, bannerId) {
  const data = await fetchJson(endpoint, { method: "POST" });
  setBanner(bannerId, data.message || "Done.", "muted");
  await pollStatus();
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

function readCameraForm() {
  return {
    width: Number(document.getElementById("cameraWidth").value || 426),
    height: Number(document.getElementById("cameraHeight").value || 240),
    fps: Number(document.getElementById("cameraFps").value || 30),
    preview_fps: Number(document.getElementById("cameraPreviewFps").value || 12),
    preview_quality: Number(document.getElementById("cameraPreviewQuality").value || 60),
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

function refreshVideoFeed() {
  const img = document.getElementById("videoFeed");
  img.src = `/video_feed?t=${Date.now()}`;
}

async function loadCameraConfig() {
  const data = await fetchJson("/api/camera/config");
  fillCameraForm(data.config || {});
  const cfg = data.config || {};
  const backend = cfg.backend ? ` Backend: ${cfg.backend}.` : "";
  const live = cfg.preview_live ? " Live preview ready." : " Preview is using placeholder.";
  const perf = ` Preview ${cfg.preview_fps ?? 12} FPS @ JPEG ${cfg.preview_quality ?? 60}.`;
  const error = cfg.last_error ? ` ${cfg.last_error}` : "";
  setBanner("cameraMessage", `Camera settings loaded.${backend}${live}${perf}${error}`.trim(), "muted");
}

async function applyCameraConfig() {
  const payload = readCameraForm();
  const button = document.getElementById("cameraApplyBtn");
  button.disabled = true;
  try {
    const data = await fetchJson("/api/camera/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    fillCameraForm(data.config || payload);
    refreshVideoFeed();
    await pollStatus();
    setBanner("cameraMessage", data.message || "Camera restarted.", data.ok ? "muted" : "warn");
  } finally {
    button.disabled = false;
  }
}

function setupJoystick() {
  const area = document.getElementById("joystickArea");
  const dot = document.getElementById("joystickDot");
  const text = document.getElementById("joystickText");

  function moveDot(clientX, clientY) {
    const rect = area.getBoundingClientRect();
    const x = clamp((clientX - rect.left) / rect.width, 0, 1);
    const y = clamp((clientY - rect.top) / rect.height, 0, 1);

    const centeredX = (x - 0.5) * 2.0;
    const scaledThrottle = (1.0 - y) * state.maxThrottle;

    state.manualSteering = clamp(centeredX, -1, 1);
    state.manualThrottle = clamp(scaledThrottle, 0, 1);

    dot.style.left = `${x * 100}%`;
    dot.style.top = `${y * 100}%`;
    dot.style.transform = "translate(-50%, -50%)";

    text.textContent = `Steering ${state.manualSteering.toFixed(2)} · Throttle ${state.manualThrottle.toFixed(2)}`;
    sendControlUpdate();
  }

  function resetDot() {
    state.manualSteering = 0;
    state.manualThrottle = 0;
    dot.style.left = "50%";
    dot.style.top = "100%";
    dot.style.transform = "translate(-50%, -100%)";
    text.textContent = "Steering 0.00 · Throttle 0.00";
    sendControlUpdate();
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
  resetDot();

  document.getElementById("stopBtn").addEventListener("click", resetDot);
}

function setupEvents() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const nextPage = btn.dataset.page;
      if (!nextPage || nextPage === state.page) return;
      renderActivePage(nextPage);
      await sendControlUpdate({ current_page: nextPage });
      if (nextPage === "camera") {
        try {
          refreshVideoFeed();
          await loadCameraConfig();
        } catch (error) {
          setBanner("cameraMessage", error.message, "muted");
        }
      }
    });
  });

  document.getElementById("saveLayoutBtn").addEventListener("click", () => {
    saveLayout(state.page, currentLayout());
    setBanner("systemMessage", `Saved ${state.page} layout.`, "muted");
  });

  document.getElementById("resetLayoutBtn").addEventListener("click", () => {
    localStorage.removeItem(layoutStorageKey(state.page));
    applyLayout(state.page);
    setBanner("systemMessage", `Reset ${state.page} layout.`, "muted");
  });

  document.getElementById("maxThrottle").addEventListener("input", (event) => {
    state.maxThrottle = Number(event.target.value) / 100;
    document.getElementById("manualSpeed").value = event.target.value;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("manualSpeed").addEventListener("input", (event) => {
    state.maxThrottle = Number(event.target.value) / 100;
    document.getElementById("maxThrottle").value = event.target.value;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("steerMix").addEventListener("input", (event) => {
    state.steerMix = Number(event.target.value) / 100;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("algorithmSelect").addEventListener("change", async (event) => {
    try {
      await fetchJson("/api/algorithm/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: event.target.value })
      });
      await pollStatus();
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
    }
  });

  document.getElementById("recordToggleBtn").addEventListener("click", async () => {
    try {
      await toggleRecording();
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
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

  document.getElementById("saveConfigBtn").addEventListener("click", async () => {
    try {
      await runSystemAction("/api/config/save", "systemMessage");
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
    }
  });

  document.getElementById("reloadConfigBtn").addEventListener("click", async () => {
    try {
      await runSystemAction("/api/config/reload", "systemMessage");
      const status = await fetchJson("/api/status");
      syncControlsFromStatus(status);
      updateStatusUi(status);
      await loadCameraConfig();
      refreshVideoFeed();
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
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
  document.getElementById("cameraWidth").addEventListener("change", setCameraResolutionPreset);
  document.getElementById("cameraHeight").addEventListener("change", setCameraResolutionPreset);

  document.getElementById("cameraReloadBtn").addEventListener("click", async () => {
    try {
      await loadCameraConfig();
      refreshVideoFeed();
    } catch (error) {
      setBanner("cameraMessage", error.message, "muted");
    }
  });

  document.getElementById("estopBtn").addEventListener("click", () => setEstop(true));
  document.getElementById("clearEstopBtn").addEventListener("click", () => setEstop(false));
}

function syncControlsFromStatus(data) {
  if (!data || typeof data !== "object") return;
  state.maxThrottle = Number(data.max_throttle || 0.55);
  state.steerMix = Number(data.steer_mix || 0.5);
  document.getElementById("maxThrottle").value = Math.round(state.maxThrottle * 100);
  document.getElementById("manualSpeed").value = Math.round(state.maxThrottle * 100);
  document.getElementById("steerMix").value = Math.round(state.steerMix * 100);
  document.getElementById("algorithmSelect").value = data.active_algorithm || "manual";
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
  setupJoystick();
  setupEvents();
  await refreshAlgorithms();
  await refreshModels();
  await loadCameraConfig();
  const status = await fetchJson("/api/status");
  updateStatusUi(status);
  syncControlsFromStatus(status);
  state.statusTimer = setInterval(pollStatus, 800);
}

window.addEventListener("load", init);
