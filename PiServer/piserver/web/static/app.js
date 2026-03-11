const gridCols = 24;
const gridRows = 14;
const layoutKeyPrefix = "PiServerLayout:";

const MODES = {
  manual: {
    key: "manual",
    label: "Manual",
    algorithm: "manual",
    settingsLabel: "Manual Settings",
    usesModel: false,
    description: "Direct driving mode. The joystick controls steering and throttle in real time.",
    behavior: "Use this mode while testing the chassis, checking camera framing, or collecting manual training data.",
    inputRule: "Joystick controls steering and throttle.",
    modelText: "Not required",
    speedLabel: "Manual speed limit",
    steerLabel: "Wheel steering mix",
    note: "Manual mode settings control direct driver response.",
    manualPanelTitle: "Manual control",
    manualPanelMini: "drag pad",
    manualPanelNote: "Joystick controls steering and throttle directly in Manual mode.",
    lockJoystick: false,
  },
  lane: {
    key: "lane",
    label: "Lane Detection",
    algorithm: "auto_steer",
    settingsLabel: "Lane Detection Settings",
    usesModel: true,
    description: "Vision-assisted mode. The model steers for you while you still set forward throttle.",
    behavior: "Use this mode when you want the PiCar to hold the lane direction but still keep speed under your hand.",
    inputRule: "Model steers. Joystick still controls throttle.",
    modelText: "Required for steering",
    speedLabel: "Lane throttle limit",
    steerLabel: "Lane steering mix",
    note: "Lane Detection uses the loaded model for steering. Keep throttle low while tuning.",
    manualPanelTitle: "Lane assist control",
    manualPanelMini: "throttle pad",
    manualPanelNote: "In Lane Detection mode the joystick still sets throttle, but steering comes from the model.",
    lockJoystick: false,
  },
  full_auto: {
    key: "full_auto",
    label: "Full Auto",
    algorithm: "autopilot",
    settingsLabel: "Full Auto Settings",
    usesModel: true,
    description: "Autonomous drive mode. The model controls both steering and throttle.",
    behavior: "Use this mode only after validating the model. The joystick pad is locked, but Stop and E-Stop always remain available.",
    inputRule: "Model controls steering and throttle.",
    modelText: "Required for steering + throttle",
    speedLabel: "Full Auto throttle limit",
    steerLabel: "Full Auto steering mix",
    note: "Full Auto locks the joystick pad and uses model output for both channels.",
    manualPanelTitle: "Manual override",
    manualPanelMini: "safety only",
    manualPanelNote: "The joystick pad is locked in Full Auto mode. Use Stop or E-Stop to interrupt motion.",
    lockJoystick: true,
  },
};

const defaultLayouts = {
  manual: {
    status: { c: 1, r: 1, w: 10, h: 3 },
    viewer: { c: 1, r: 4, w: 15, h: 9 },
    drive: { c: 16, r: 1, w: 9, h: 6 },
    manual: { c: 16, r: 7, w: 9, h: 6 },
    record: { c: 1, r: 13, w: 8, h: 2 },
    system: { c: 9, r: 13, w: 16, h: 2 },
  },
  lane: {
    status: { c: 1, r: 1, w: 9, h: 3 },
    viewer: { c: 1, r: 4, w: 14, h: 9 },
    drive: { c: 15, r: 1, w: 10, h: 7 },
    manual: { c: 15, r: 8, w: 10, h: 5 },
    record: { c: 1, r: 13, w: 8, h: 2 },
    system: { c: 9, r: 13, w: 16, h: 2 },
  },
  full_auto: {
    status: { c: 1, r: 1, w: 8, h: 3 },
    viewer: { c: 1, r: 4, w: 16, h: 9 },
    drive: { c: 17, r: 1, w: 8, h: 7 },
    manual: { c: 17, r: 8, w: 8, h: 5 },
    record: { c: 1, r: 13, w: 7, h: 2 },
    system: { c: 8, r: 13, w: 17, h: 2 },
  },
  calibration: {
    status: { c: 1, r: 1, w: 8, h: 3 },
    viewer: { c: 1, r: 4, w: 13, h: 9 },
    drive: { c: 14, r: 1, w: 11, h: 8 },
    manual: { c: 14, r: 9, w: 11, h: 4 },
    record: { c: 1, r: 13, w: 6, h: 2 },
    system: { c: 7, r: 13, w: 18, h: 2 },
  },
  camera: {
    status: { c: 1, r: 1, w: 8, h: 3 },
    viewer: { c: 1, r: 4, w: 13, h: 9 },
    drive: { c: 14, r: 1, w: 11, h: 8 },
    manual: { c: 14, r: 9, w: 11, h: 4 },
    record: { c: 1, r: 13, w: 6, h: 2 },
    system: { c: 7, r: 13, w: 18, h: 2 },
  },
};

const CAMERA_RESOLUTIONS = [
  "320x240",
  "426x240",
  "640x360",
  "640x480",
  "800x600",
];

const state = {
  page: "manual",
  driveMode: "manual",
  modeView: "overview",
  manualSteering: 0,
  manualThrottle: 0,
  dragging: null,
  resizing: null,
  latestStatus: null,
  modeProfiles: defaultModeProfiles(),
  calibration: defaultCalibration(),
  pendingControlTimer: null,
  statusTimer: null,
  statusTick: 0,
  videoActive: true,
};

function defaultModeProfiles() {
  return {
    manual: { max_throttle: 0.55, steer_mix: 0.5 },
    lane: { max_throttle: 0.4, steer_mix: 0.58 },
    full_auto: { max_throttle: 0.45, steer_mix: 0.55 },
  };
}

function defaultCalibration() {
  return {
    left_motor_scale: 1.0,
    right_motor_scale: 1.0,
    global_speed_limit: 0.75,
    turn_gain: 1.0,
    camera_width: 426,
    camera_height: 240,
    camera_fps: 30,
    camera_format: "BGR888",
    auto_exposure: true,
    exposure_time: 12000,
    analogue_gain: 1.5,
    exposure_compensation: 0.0,
    auto_white_balance: true,
    brightness: 0.0,
    contrast: 1.0,
    saturation: 1.0,
    sharpness: 1.0,
  };
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizePage(page) {
  const value = String(page || "manual").toLowerCase();
  if (["training", "lane_detection", "auto_steer", "lane"].includes(value)) return "lane";
  if (["auto", "autopilot", "full_auto"].includes(value)) return "full_auto";
  if (["calibration", "calibrate"].includes(value)) return "calibration";
  if (["camera", "camera_settings", "settings"].includes(value)) return "camera";
  return MODES[value] ? value : "manual";
}

function normalizeMode(mode) {
  const page = normalizePage(mode);
  return ["calibration", "camera"].includes(page) ? state.driveMode : page;
}

function currentMode() {
  return MODES[normalizeMode(state.driveMode)] || MODES.manual;
}

function currentProfile() {
  const mode = normalizeMode(state.driveMode);
  const defaults = defaultModeProfiles();
  const saved = state.modeProfiles?.[mode] || {};
  return {
    max_throttle: Number(saved.max_throttle ?? defaults[mode].max_throttle),
    steer_mix: Number(saved.steer_mix ?? defaults[mode].steer_mix),
  };
}

function setCurrentProfile(partial) {
  const mode = normalizeMode(state.driveMode);
  const merged = { ...currentProfile(), ...partial };
  state.modeProfiles = { ...state.modeProfiles, [mode]: merged };
  return merged;
}

function currentCalibration() {
  return { ...defaultCalibration(), ...(state.calibration || {}) };
}

function currentCameraSettings() {
  return currentCalibration();
}

function panelEls() {
  return Array.from(document.querySelectorAll(".dock-panel"));
}

function layoutStorageKey(page) {
  return `${layoutKeyPrefix}${page}`;
}

function loadLayout(page) {
  const safePage = normalizePage(page);
  try {
    const raw = localStorage.getItem(layoutStorageKey(safePage));
    if (!raw) return deepClone(defaultLayouts[safePage]);
    const parsed = JSON.parse(raw);
    return Object.assign(deepClone(defaultLayouts[safePage]), parsed);
  } catch {
    return deepClone(defaultLayouts[safePage]);
  }
}

function saveLayout(page, layout) {
  localStorage.setItem(layoutStorageKey(normalizePage(page)), JSON.stringify(layout));
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
    const style = getComputedStyle(panel);
    out[panel.dataset.panel] = {
      c: Number(style.getPropertyValue("--c")) || 1,
      r: Number(style.getPropertyValue("--r")) || 1,
      w: Number(style.getPropertyValue("--w")) || 6,
      h: Number(style.getPropertyValue("--h")) || 3,
    };
  });
  return out;
}

function readPanelBox(panel) {
  const style = getComputedStyle(panel);
  return {
    c: Number(style.getPropertyValue("--c")) || 1,
    r: Number(style.getPropertyValue("--r")) || 1,
    w: Number(style.getPropertyValue("--w")) || 6,
    h: Number(style.getPropertyValue("--h")) || 3,
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
    cellH: rect.height / gridRows,
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
        offsetY: event.clientY - rect.top - (box.r - 1) * cellH,
      };
      head.setPointerCapture(event.pointerId);
    });

    handle.addEventListener("pointerdown", (event) => {
      const box = readPanelBox(panel);
      panel.classList.add("resizing");
      state.resizing = {
        panel,
        startX: event.clientX,
        startY: event.clientY,
        box,
      };
      handle.setPointerCapture(event.pointerId);
      event.stopPropagation();
    });
  });

  window.addEventListener("pointermove", (event) => {
    if (state.dragging) {
      const { rect, cellW, cellH } = workspaceMetrics();
      const drag = state.dragging;
      const left = event.clientX - rect.left - drag.offsetX;
      const top = event.clientY - rect.top - drag.offsetY;
      const c = clamp(Math.round(left / cellW) + 1, 1, gridCols - drag.box.w + 1);
      const r = clamp(Math.round(top / cellH) + 1, 1, gridRows - drag.box.h + 1);
      setPanelBox(drag.panel, { ...drag.box, c, r });
    }
    if (state.resizing) {
      const resize = state.resizing;
      const { cellW, cellH } = workspaceMetrics();
      const dx = event.clientX - resize.startX;
      const dy = event.clientY - resize.startY;
      const newW = clamp(Math.round(resize.box.w + dx / cellW), 3, gridCols - resize.box.c + 1);
      const newH = clamp(Math.round(resize.box.h + dy / cellH), 2, gridRows - resize.box.r + 1);
      setPanelBox(resize.panel, { ...resize.box, w: newW, h: newH });
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

function setBanner(id, text, tone = "muted") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.className = `banner ${tone}`;
}

function friendlyAlgorithmLabel(name) {
  const labelMap = {
    manual: "Manual",
    auto_steer: "Lane Detection",
    autopilot: "Full Auto",
    stop: "Stop",
  };
  return labelMap[name] || name || "unknown";
}

function currentPageLabel() {
  if (state.page === "calibration") return "Calibration";
  if (state.page === "camera") return "Camera";
  return currentMode().label;
}

function setModeView(view) {
  state.modeView = view === "settings" ? "settings" : "overview";
  document.querySelectorAll(".subtab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === state.modeView);
  });
  document.getElementById("modeOverviewView").classList.toggle("hidden", state.modeView !== "overview");
  document.getElementById("modeSettingsView").classList.toggle("hidden", state.modeView !== "settings");
}

function selectResolutionValue(width, height) {
  const value = `${width}x${height}`;
  const select = document.getElementById("cameraResolution");
  if (!CAMERA_RESOLUTIONS.includes(value) && !Array.from(select.options).some((opt) => opt.value === value)) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = `${width} × ${height} (custom)`;
    select.appendChild(opt);
  }
  select.value = value;
}

function populateCalibrationControls() {
  const calibration = currentCalibration();
  document.getElementById("leftMotorScale").value = Math.round(calibration.left_motor_scale * 100);
  document.getElementById("rightMotorScale").value = Math.round(calibration.right_motor_scale * 100);
  document.getElementById("globalSpeedLimit").value = Math.round(calibration.global_speed_limit * 100);
  document.getElementById("turnGain").value = Math.round(calibration.turn_gain * 100);
  updateCalibrationValueText();
}

function populateCameraControls() {
  const camera = currentCameraSettings();
  selectResolutionValue(camera.camera_width, camera.camera_height);
  document.getElementById("cameraFps").value = String(camera.camera_fps);
  document.getElementById("cameraFormat").value = camera.camera_format;
  document.getElementById("cameraAutoExposure").checked = !!camera.auto_exposure;
  document.getElementById("cameraExposureTime").value = Math.round(camera.exposure_time || 12000);
  document.getElementById("cameraAnalogueGain").value = Math.round((camera.analogue_gain || 1.5) * 10);
  document.getElementById("cameraExposureCompensation").value = Math.round((camera.exposure_compensation || 0) * 10);
  document.getElementById("cameraAutoWhiteBalance").checked = !!camera.auto_white_balance;
  document.getElementById("cameraBrightness").value = Math.round((camera.brightness || 0) * 100);
  document.getElementById("cameraContrast").value = Math.round((camera.contrast || 1) * 100);
  document.getElementById("cameraSaturation").value = Math.round((camera.saturation || 1) * 100);
  document.getElementById("cameraSharpness").value = Math.round((camera.sharpness || 1) * 100);
  updateCameraValueText();
}

function updateCalibrationValueText() {
  const calibration = currentCalibration();
  document.getElementById("leftMotorScaleValue").textContent = Number(calibration.left_motor_scale).toFixed(2);
  document.getElementById("rightMotorScaleValue").textContent = Number(calibration.right_motor_scale).toFixed(2);
  document.getElementById("globalSpeedLimitValue").textContent = Number(calibration.global_speed_limit).toFixed(2);
  document.getElementById("turnGainValue").textContent = Number(calibration.turn_gain).toFixed(2);
}

function updateCameraValueText() {
  const camera = readCameraFromForm();
  document.getElementById("cameraExposureTimeValue").textContent = String(Math.round(camera.exposure_time));
  document.getElementById("cameraAnalogueGainValue").textContent = Number(camera.analogue_gain).toFixed(1);
  document.getElementById("cameraExposureCompensationValue").textContent = Number(camera.exposure_compensation).toFixed(1);
  document.getElementById("cameraBrightnessValue").textContent = Number(camera.brightness).toFixed(2);
  document.getElementById("cameraContrastValue").textContent = Number(camera.contrast).toFixed(2);
  document.getElementById("cameraSaturationValue").textContent = Number(camera.saturation).toFixed(2);
  document.getElementById("cameraSharpnessValue").textContent = Number(camera.sharpness).toFixed(2);
  const locked = !camera.auto_exposure;
  document.getElementById("cameraExposureTime").disabled = !locked;
  document.getElementById("cameraAnalogueGain").disabled = !locked;
}

function readCalibrationFromForm() {
  return {
    left_motor_scale: Number(document.getElementById("leftMotorScale").value) / 100,
    right_motor_scale: Number(document.getElementById("rightMotorScale").value) / 100,
    global_speed_limit: Number(document.getElementById("globalSpeedLimit").value) / 100,
    turn_gain: Number(document.getElementById("turnGain").value) / 100,
  };
}

function readCameraFromForm() {
  const resolution = String(document.getElementById("cameraResolution").value || "426x240").split("x");
  return {
    camera_width: Number(resolution[0] || 426),
    camera_height: Number(resolution[1] || 240),
    camera_fps: Number(document.getElementById("cameraFps").value || 30),
    camera_format: document.getElementById("cameraFormat").value || "BGR888",
    auto_exposure: document.getElementById("cameraAutoExposure").checked,
    exposure_time: Number(document.getElementById("cameraExposureTime").value || 12000),
    analogue_gain: Number(document.getElementById("cameraAnalogueGain").value || 15) / 10,
    exposure_compensation: Number(document.getElementById("cameraExposureCompensation").value || 0) / 10,
    auto_white_balance: document.getElementById("cameraAutoWhiteBalance").checked,
    brightness: Number(document.getElementById("cameraBrightness").value || 0) / 100,
    contrast: Number(document.getElementById("cameraContrast").value || 100) / 100,
    saturation: Number(document.getElementById("cameraSaturation").value || 100) / 100,
    sharpness: Number(document.getElementById("cameraSharpness").value || 100) / 100,
  };
}

function renderModeWorkspace() {
  const calibrationPage = state.page === "calibration";
  const cameraPage = state.page === "camera";
  const mode = currentMode();
  const profile = currentProfile();

  document.getElementById("workspacePanelTitle").textContent = calibrationPage ? "Calibration workspace" : (cameraPage ? "Camera workspace" : "Mode workspace");
  document.getElementById("currentModeBadge").textContent = calibrationPage ? "Calibration" : (cameraPage ? "Camera" : mode.label);
  document.getElementById("modeWorkspaceTabs").classList.toggle("hidden", calibrationPage || cameraPage);
  document.getElementById("modeOverviewView").classList.toggle("hidden", calibrationPage || cameraPage || state.modeView !== "overview");
  document.getElementById("modeSettingsView").classList.toggle("hidden", calibrationPage || cameraPage || state.modeView !== "settings");
  document.getElementById("calibrationView").classList.toggle("hidden", !calibrationPage);
  document.getElementById("cameraView").classList.toggle("hidden", !cameraPage);

  document.getElementById("currentModeTitle").textContent = mode.label;
  document.getElementById("currentModeDescription").textContent = mode.description;
  document.getElementById("modeCurrentAlgorithm").textContent = friendlyAlgorithmLabel(mode.algorithm);
  document.getElementById("modeInputRule").textContent = mode.inputRule;
  document.getElementById("modeModelRequirement").textContent = mode.modelText;
  document.getElementById("modeBehaviorText").textContent = mode.behavior;
  document.getElementById("modeSettingsTab").textContent = mode.settingsLabel;
  document.getElementById("modeMaxThrottleLabel").textContent = mode.speedLabel;
  document.getElementById("modeSteerMixLabel").textContent = mode.steerLabel;
  document.getElementById("modeSettingsNote").textContent = mode.note;

  const joystickArea = document.getElementById("joystickArea");
  joystickArea.classList.toggle("locked", !!mode.lockJoystick && !calibrationPage && !cameraPage);

  if (calibrationPage) {
    document.getElementById("manualPanelTitle").textContent = "Calibration test drive";
    document.getElementById("manualPanelMini").textContent = "live check";
    document.getElementById("manualModeNote").textContent = `Drive mode stays on ${mode.label} while you tune motor trims and speed limits.`;
    document.getElementById("manualSpeedLabel").textContent = `${mode.label} speed limit`;
    populateCalibrationControls();
  populateCameraControls();
  } else if (cameraPage) {
    document.getElementById("manualPanelTitle").textContent = "Camera test drive";
    document.getElementById("manualPanelMini").textContent = "view check";
    document.getElementById("manualModeNote").textContent = `Drive mode stays on ${mode.label} while you tune exposure, colour, and stream setup.`;
    document.getElementById("manualSpeedLabel").textContent = `${mode.label} speed limit`;
    populateCameraControls();
  } else {
    document.getElementById("manualPanelTitle").textContent = mode.manualPanelTitle;
    document.getElementById("manualPanelMini").textContent = mode.manualPanelMini;
    document.getElementById("manualModeNote").textContent = mode.manualPanelNote;
    document.getElementById("manualSpeedLabel").textContent = mode.speedLabel;
  }

  document.getElementById("modelToolsGroup").classList.toggle("hidden", !mode.usesModel);
  document.getElementById("modeMaxThrottle").value = Math.round(profile.max_throttle * 100);
  document.getElementById("modeSteerMix").value = Math.round(profile.steer_mix * 100);
  document.getElementById("manualSpeed").value = Math.round(profile.max_throttle * 100);
  updateRangeText();
}

function updateRangeText() {
  const profile = currentProfile();
  document.getElementById("modeMaxThrottleValue").textContent = profile.max_throttle.toFixed(2);
  document.getElementById("modeSteerMixValue").textContent = profile.steer_mix.toFixed(2);
  document.getElementById("manualSpeedValue").textContent = profile.max_throttle.toFixed(2);
}

function setActivePage(page) {
  const normalized = normalizePage(page);
  const changed = state.page !== normalized;
  state.page = normalized;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === normalized);
  });
  if (changed) {
    applyLayout(normalized);
  }
  renderModeWorkspace();
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || "Request failed");
  }
  return data;
}

async function postControlUpdate(extra = {}) {
  const profile = currentProfile();
  const body = {
    steering: state.manualSteering,
    throttle: state.manualThrottle,
    max_throttle: profile.max_throttle,
    steer_mix: profile.steer_mix,
    current_page: state.page,
    ...extra,
  };
  try {
    await fetchJson("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    setBanner("statusBanner", error.message, "muted");
  }
}

function sendControlUpdate(extra = {}, immediate = false) {
  if (immediate) {
    if (state.pendingControlTimer) {
      clearTimeout(state.pendingControlTimer);
      state.pendingControlTimer = null;
    }
    return postControlUpdate(extra);
  }
  if (state.pendingControlTimer) return;
  state.pendingControlTimer = window.setTimeout(async () => {
    state.pendingControlTimer = null;
    await postControlUpdate(extra);
  }, 50);
}

function syncControlsFromStatus(data) {
  state.latestStatus = data;
  state.modeProfiles = { ...defaultModeProfiles(), ...(data.mode_profiles || {}) };
  state.calibration = { ...defaultCalibration(), ...(data.calibration || {}) };
  state.driveMode = normalizeMode(data.drive_mode || data.current_page || state.driveMode);
  const nextPage = normalizePage(data.current_page || state.page);
  setActivePage(nextPage);
}

function updateStatusUi(data) {
  syncControlsFromStatus(data);
  document.getElementById("metricModeLabel").textContent = currentMode().label;
  document.getElementById("metricAlgorithm").textContent = friendlyAlgorithmLabel(data.active_algorithm);
  document.getElementById("metricModel").textContent = data.active_model || "none";
  document.getElementById("metricFps").textContent = Number(data.fps || 0).toFixed(1);
  document.getElementById("metricRec").textContent = data.recording ? "on" : "off";
  document.getElementById("metricWheels").textContent = `${Number(data.motor_left).toFixed(2)} / ${Number(data.motor_right).toFixed(2)}`;
  document.getElementById("metricCamera").textContent = `${data.camera_backend} ${data.camera_width}×${data.camera_height}`;
  document.getElementById("metricEstop").textContent = data.safety_stop ? "engaged" : "clear";
  setBanner("statusBanner", data.system_message || "Ready.", "muted");

  const badge = document.getElementById("recordStateBadge");
  badge.textContent = data.recording ? "on" : "off";
  badge.classList.toggle("on", !!data.recording);
  badge.classList.toggle("off", !data.recording);

  populateCalibrationControls();
  populateCameraControls();
}

async function refreshGitStatus(force = false) {
  try {
    const data = await fetchJson(`/api/system/git_status${force ? "?force=1" : ""}`);
    const gitText = data.ok
      ? `${data.branch} · ${data.commit}${data.dirty ? " · modified" : ""} · ${data.project_rel || "PiServer"}`
      : (data.message || "No Git repo");
    document.getElementById("gitStatusText").textContent = gitText;
  } catch (error) {
    document.getElementById("gitStatusText").textContent = error.message;
  }
}

async function pollStatus() {
  try {
    const data = await fetchJson("/api/status");
    updateStatusUi(data);
    state.statusTick += 1;
    if (state.statusTick === 1 || state.statusTick % 8 === 0) {
      await refreshGitStatus(state.statusTick === 1);
    }
  } catch (error) {
    setBanner("systemMessage", error.message, "muted");
  }
}

function scheduleStatusPoll() {
  if (state.statusTimer) {
    window.clearInterval(state.statusTimer);
    state.statusTimer = null;
  }
  const intervalMs = document.hidden ? 5000 : 1500;
  state.statusTimer = window.setInterval(pollStatus, intervalMs);
}

function updateVideoStreamVisibility() {
  const video = document.getElementById("videoFeed");
  if (!video) return;
  const shouldBeActive = !document.hidden;
  if (shouldBeActive === state.videoActive) return;
  state.videoActive = shouldBeActive;
  video.src = shouldBeActive ? "/video_feed" : "";
}

async function refreshModels() {
  try {
    const data = await fetchJson("/api/model/list");
    const select = document.getElementById("modelSelect");
    select.innerHTML = "";
    if (!data.models.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(none)";
      select.appendChild(opt);
    } else {
      data.models.forEach((name) => {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        select.appendChild(opt);
      });
    }
    if (data.active && data.active !== "none") {
      select.value = data.active;
    }
  } catch (error) {
    setBanner("modelMessage", error.message, "muted");
  }
}

async function uploadModel() {
  const fileInput = document.getElementById("modelFile");
  if (!fileInput.files.length) {
    setBanner("modelMessage", "Choose a .tflite file first.", "muted");
    return;
  }
  const form = new FormData();
  form.append("file", fileInput.files[0]);
  const response = await fetch("/api/model/upload", { method: "POST", body: form });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || "Upload failed");
  }
  setBanner("modelMessage", data.message || "Model uploaded.", "muted");
  await refreshModels();
}

async function loadSelectedModel() {
  const select = document.getElementById("modelSelect");
  if (!select.value) {
    setBanner("modelMessage", "Select a model first.", "muted");
    return;
  }
  const data = await fetchJson("/api/model/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename: select.value }),
  });
  setBanner("modelMessage", data.message || "Model loaded.", "muted");
  await pollStatus();
}

async function toggleRecording() {
  await fetchJson("/api/record/toggle", { method: "POST" });
  await pollStatus();
}

async function setEstop(enabled) {
  await fetchJson("/api/system/estop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  await pollStatus();
}

async function runSystemAction(endpoint, bannerId) {
  try {
    const data = await fetchJson(endpoint, { method: "POST" });
    setBanner(bannerId, data.message || "Done.", "muted");
    await pollStatus();
  } catch (error) {
    setBanner(bannerId, error.message, "muted");
  }
}

async function switchPage(page) {
  const nextPage = normalizePage(page);
  try {
    const data = await fetchJson("/api/page/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page: nextPage }),
    });
    if (data.state) {
      updateStatusUi(data.state);
    }
  } catch (error) {
    setBanner("statusBanner", error.message, "muted");
  }
}

async function applyCalibration() {
  try {
    const payload = readCalibrationFromForm();
    state.calibration = { ...state.calibration, ...payload };
    updateCalibrationValueText();
    const data = await fetchJson("/api/calibration/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (data.state) {
      updateStatusUi(data.state);
    }
    setBanner("calibrationMessage", data.message || "Calibration applied.", "muted");
  } catch (error) {
    setBanner("calibrationMessage", error.message, "muted");
  }
}

async function applyCameraSettings() {
  try {
    const payload = readCameraFromForm();
    state.calibration = { ...state.calibration, ...payload };
    updateCameraValueText();
    const data = await fetchJson("/api/camera/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (data.state) {
      updateStatusUi(data.state);
    }
    setBanner("cameraMessage", data.message || "Camera settings applied.", "muted");
  } catch (error) {
    setBanner("cameraMessage", error.message, "muted");
  }
}

function setupJoystick() {
  const area = document.getElementById("joystickArea");
  const dot = document.getElementById("joystickDot");
  const text = document.getElementById("joystickText");

  function moveDot(clientX, clientY) {
    if (currentMode().lockJoystick && !["calibration", "camera"].includes(state.page)) return;
    const rect = area.getBoundingClientRect();
    const x = clamp((clientX - rect.left) / rect.width, 0, 1);
    const y = clamp((clientY - rect.top) / rect.height, 0, 1);

    const centeredX = (x - 0.5) * 2.0;
    const scaledThrottle = (1.0 - y) * currentProfile().max_throttle;

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
    sendControlUpdate({}, true);
  }

  area.addEventListener("pointerdown", (event) => {
    if (currentMode().lockJoystick && !["calibration", "camera"].includes(state.page)) {
      setBanner("statusBanner", "Joystick pad is locked in Full Auto mode.", "muted");
      return;
    }
    area.setPointerCapture(event.pointerId);
    moveDot(event.clientX, event.clientY);
  });
  area.addEventListener("pointermove", (event) => {
    if (event.buttons && !(currentMode().lockJoystick && !["calibration", "camera"].includes(state.page))) moveDot(event.clientX, event.clientY);
  });
  area.addEventListener("pointerup", resetDot);
  area.addEventListener("pointercancel", resetDot);
  resetDot();

  document.getElementById("stopBtn").addEventListener("click", resetDot);
}

function setupEvents() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchPage(btn.dataset.page));
  });

  document.querySelectorAll(".subtab-btn").forEach((btn) => {
    btn.addEventListener("click", () => setModeView(btn.dataset.view));
  });

  document.getElementById("saveLayoutBtn").addEventListener("click", () => {
    saveLayout(state.page, currentLayout());
    setBanner("systemMessage", `Saved ${currentPageLabel()} layout.`, "muted");
  });

  document.getElementById("resetLayoutBtn").addEventListener("click", () => {
    localStorage.removeItem(layoutStorageKey(state.page));
    applyLayout(state.page);
    setBanner("systemMessage", `Reset ${currentPageLabel()} layout.`, "muted");
  });

  document.getElementById("modeMaxThrottle").addEventListener("input", (event) => {
    const maxThrottle = Number(event.target.value) / 100;
    setCurrentProfile({ max_throttle: maxThrottle });
    document.getElementById("manualSpeed").value = event.target.value;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("manualSpeed").addEventListener("input", (event) => {
    const maxThrottle = Number(event.target.value) / 100;
    setCurrentProfile({ max_throttle: maxThrottle });
    document.getElementById("modeMaxThrottle").value = event.target.value;
    updateRangeText();
    sendControlUpdate();
  });

  document.getElementById("modeSteerMix").addEventListener("input", (event) => {
    const steerMix = Number(event.target.value) / 100;
    setCurrentProfile({ steer_mix: steerMix });
    updateRangeText();
    sendControlUpdate();
  });

  [
    ["leftMotorScale", "left_motor_scale"],
    ["rightMotorScale", "right_motor_scale"],
    ["globalSpeedLimit", "global_speed_limit"],
    ["turnGain", "turn_gain"],
  ].forEach(([id, key]) => {
    document.getElementById(id).addEventListener("input", (event) => {
      state.calibration = { ...state.calibration, [key]: Number(event.target.value) / 100 };
      updateCalibrationValueText();
    });
  });

  [
    "cameraResolution", "cameraFps", "cameraFormat", "cameraAutoExposure", "cameraExposureTime",
    "cameraAnalogueGain", "cameraExposureCompensation", "cameraAutoWhiteBalance", "cameraBrightness",
    "cameraContrast", "cameraSaturation", "cameraSharpness"
  ].forEach((id) => {
    const el = document.getElementById(id);
    const evt = el.type === "checkbox" || el.tagName === "SELECT" ? "change" : "input";
    el.addEventListener(evt, () => {
      const values = readCameraFromForm();
      state.calibration = { ...state.calibration, ...values };
      updateCameraValueText();
    });
  });

  document.getElementById("applyCalibrationBtn").addEventListener("click", applyCalibration);
  document.getElementById("refreshCalibrationBtn").addEventListener("click", () => {
    populateCalibrationControls();
    setBanner("calibrationMessage", "Loaded current runtime calibration values.", "muted");
  });
  document.getElementById("applyCameraBtn").addEventListener("click", applyCameraSettings);
  document.getElementById("refreshCameraBtn").addEventListener("click", () => {
    populateCameraControls();
    setBanner("cameraMessage", "Loaded current camera values.", "muted");
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
      await pollStatus();
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
    }
  });

  document.getElementById("gitPullBtn").addEventListener("click", () => runSystemAction("/api/system/update", "systemMessage"));
  document.addEventListener("visibilitychange", () => {
    updateVideoStreamVisibility();
    scheduleStatusPoll();
  });
  document.getElementById("restartBtn").addEventListener("click", () => runSystemAction("/api/system/restart", "systemMessage"));
  document.getElementById("estopBtn").addEventListener("click", () => setEstop(true));
  document.getElementById("clearEstopBtn").addEventListener("click", () => setEstop(false));
}

async function init() {
  applyLayout(state.page);
  renderModeWorkspace();
  setModeView("overview");
  setupDocking();
  setupJoystick();
  setupEvents();
  updateVideoStreamVisibility();
  await refreshModels();
  const status = await fetchJson("/api/status");
  updateStatusUi(status);
  await refreshGitStatus(true);
  scheduleStatusPoll();
}

window.addEventListener("load", init);
