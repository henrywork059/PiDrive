const gridCols = 45;
const gridRows = 25;
const layoutKeyPrefix = "PiServerLayout:v0_3_6:";
const manualFeelKey = "PiServerManualFeel:v0_3_5";
const STEP_INTERVAL_MS = 60;
const STEP_SIZE = 0.08;

const pagePanels = {
  manual: ["status", "estop", "viewer", "runtime", "manual", "record"],
  training: ["status", "estop", "viewer", "model", "manual", "record", "sessions"],
  auto: ["status", "estop", "viewer", "runtime", "model", "record"],
  camera: ["status", "estop", "viewer", "camera"],
  motor: ["status", "estop", "viewer", "motor"]
};

const defaultLayouts = {
  manual: {
    status: { c: 1, r: 1, w: 6, h: 14 },
    estop: { c: 1, r: 15, w: 6, h: 4 },
    record: { c: 1, r: 19, w: 6, h: 4 },
    viewer: { c: 7, r: 1, w: 21, h: 22 },
    runtime: { c: 28, r: 1, w: 18, h: 6 },
    manual: { c: 28, r: 7, w: 18, h: 16 }
  },
  training: {
    status: { c: 1, r: 1, w: 20, h: 5 },
    estop: { c: 21, r: 1, w: 6, h: 5 },
    viewer: { c: 1, r: 6, w: 24, h: 15 },
    model: { c: 25, r: 6, w: 21, h: 5 },
    manual: { c: 25, r: 11, w: 21, h: 10 },
    record: { c: 1, r: 21, w: 24, h: 5 },
    sessions: { c: 25, r: 21, w: 21, h: 5 }
  },
  auto: {
    status: { c: 1, r: 1, w: 35, h: 5 },
    estop: { c: 36, r: 1, w: 10, h: 5 },
    viewer: { c: 1, r: 6, w: 28, h: 15 },
    runtime: { c: 29, r: 6, w: 17, h: 6 },
    model: { c: 29, r: 12, w: 17, h: 9 },
    record: { c: 1, r: 21, w: 20, h: 5 }
  },
  camera: {
    status: { c: 1, r: 1, w: 35, h: 5 },
    estop: { c: 36, r: 1, w: 10, h: 5 },
    viewer: { c: 1, r: 6, w: 22, h: 20 },
    camera: { c: 23, r: 6, w: 23, h: 20 }
  },
  motor: {
    status: { c: 1, r: 1, w: 35, h: 5 },
    estop: { c: 36, r: 1, w: 10, h: 5 },
    viewer: { c: 1, r: 6, w: 22, h: 20 },
    motor: { c: 23, r: 6, w: 23, h: 20 }
  }
};

const state = {
  page: "manual",
  manualSteering: 0,
  manualThrottle: 0,
  rawTargetSteering: 0,
  rawTargetThrottle: 0,
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
  overlayMode: 0,
  capturePending: false,
  sessions: [],
  selectedSession: "",
  steerCurve: 1.45,
  throttleCurve: 1.55,
  steerRate: 0.07,
  throttleRate: 0.07,
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


function curveInput(value, exponent) {
  const clamped = clamp(Number(value || 0), -1, 1);
  const exp = clamp(Number(exponent || 1), 1, 3);
  return Math.sign(clamped) * Math.pow(Math.abs(clamped), exp);
}

function updateDerivedTargets() {
  state.targetSteering = curveInput(state.rawTargetSteering, state.steerCurve);
  state.targetThrottle = curveInput(state.rawTargetThrottle, state.throttleCurve) * state.maxThrottle;
}

function formatElapsed(totalSeconds) {
  const whole = Math.max(0, Math.floor(Number(totalSeconds || 0)));
  const minutes = Math.floor(whole / 60);
  const seconds = whole % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function triggerSnapshotFlash() {
  const flash = document.getElementById("snapshotFlash");
  if (!flash) return;
  flash.classList.remove("active");
  void flash.offsetWidth;
  flash.classList.add("active");
}

function updateManualFeelUi() {
  const values = [
    ["steerCurve", Math.round(state.steerCurve * 100)],
    ["throttleCurve", Math.round(state.throttleCurve * 100)],
    ["steerRate", Math.round(state.steerRate * 100)],
    ["throttleRate", Math.round(state.throttleRate * 100)],
  ];
  values.forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.value = value;
  });
  const steerCurveValue = document.getElementById("steerCurveValue");
  const throttleCurveValue = document.getElementById("throttleCurveValue");
  const steerRateValue = document.getElementById("steerRateValue");
  const throttleRateValue = document.getElementById("throttleRateValue");
  if (steerCurveValue) steerCurveValue.textContent = `${state.steerCurve.toFixed(2)}×`;
  if (throttleCurveValue) throttleCurveValue.textContent = `${state.throttleCurve.toFixed(2)}×`;
  if (steerRateValue) steerRateValue.textContent = state.steerRate.toFixed(2);
  if (throttleRateValue) throttleRateValue.textContent = state.throttleRate.toFixed(2);
}

function saveManualFeel() {
  try {
    localStorage.setItem(manualFeelKey, JSON.stringify({
      steerCurve: state.steerCurve,
      throttleCurve: state.throttleCurve,
      steerRate: state.steerRate,
      throttleRate: state.throttleRate,
    }));
  } catch {}
}

function loadManualFeel() {
  try {
    const raw = localStorage.getItem(manualFeelKey);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (typeof parsed.steerCurve === "number") state.steerCurve = clamp(parsed.steerCurve, 1, 3);
    if (typeof parsed.throttleCurve === "number") state.throttleCurve = clamp(parsed.throttleCurve, 1, 3);
    if (typeof parsed.steerRate === "number") state.steerRate = clamp(parsed.steerRate, 0.02, 0.2);
    if (typeof parsed.throttleRate === "number") state.throttleRate = clamp(parsed.throttleRate, 0.02, 0.2);
  } catch {}
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
  updateManualFeelUi();
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

function setOverlayMode(mode) {
  const normalized = ((Number(mode) || 0) % 3 + 3) % 3;
  state.overlayMode = normalized;
  const btn = document.getElementById("overlayToggleBtn");
  if (btn) {
    btn.classList.remove("off", "mode-1", "mode-2");
    btn.classList.add(normalized === 0 ? "off" : `mode-${normalized}`);
    btn.setAttribute("aria-pressed", normalized === 0 ? "false" : "true");
    const value = btn.querySelector(".metric-card-action-value");
    const note = btn.querySelector(".metric-card-action-note");
    if (value) value.textContent = normalized === 0 ? "OFF" : `OVL ${normalized}`;
    if (note) {
      note.textContent = normalized === 1
        ? "Throttle + steering"
        : normalized === 2
          ? "Overlay 2 placeholder"
          : "Click to cycle overlays";
    }
  }
  const frameOverlay = document.getElementById("frameOverlay");
  if (frameOverlay) {
    frameOverlay.classList.remove("overlay-mode-0", "overlay-mode-1", "overlay-mode-2");
    frameOverlay.classList.add(`overlay-mode-${normalized}`);
  }
  updateOverlayVisuals(state.latestStatus || {});
}

function updateOverlayVisuals(data = {}) {
  const throttleFill = document.getElementById("overlayThrottleFill");
  const throttleValue = document.getElementById("overlayThrottleValue");
  const steerArcLeft = document.getElementById("overlaySteerArcLeft");
  const steerArcRight = document.getElementById("overlaySteerArcRight");
  const steerValue = document.getElementById("overlaySteerValue");
  const steerNeedle = document.getElementById("overlaySteerNeedle");
  const appliedThrottle = Number(data.applied_throttle || 0);
  const appliedSteering = Number(data.applied_steering || 0);
  const throttleNormBase = Math.max(0.01, Number(data.max_throttle ?? state.maxThrottle ?? 1));
  const throttleNorm = clamp(appliedThrottle / throttleNormBase, -1, 1);
  if (throttleFill) {
    const halfPct = Math.abs(throttleNorm) * 50;
    throttleFill.style.height = `${halfPct}%`;
    throttleFill.style.top = throttleNorm >= 0 ? `${50 - halfPct}%` : "50%";
  }
  if (throttleValue) throttleValue.textContent = appliedThrottle.toFixed(2);
  const steerNorm = clamp(appliedSteering, -1, 1);
  const steerMagnitude = Math.abs(steerNorm) * 50;
  if (steerArcLeft) {
    steerArcLeft.style.strokeDasharray = steerNorm < 0 ? `${steerMagnitude} 100` : `0 100`;
    steerArcLeft.style.strokeDashoffset = steerNorm < 0 ? `${steerMagnitude - 50}` : `0`;
  }
  if (steerArcRight) {
    steerArcRight.style.strokeDasharray = steerNorm > 0 ? `${steerMagnitude} 100` : `0 100`;
    steerArcRight.style.strokeDashoffset = `-50`;
  }
  if (steerNeedle) {
    const angle = steerNorm * 90;
    steerNeedle.style.transform = `rotate(${angle}deg)`;
  }
  if (steerValue) steerValue.textContent = appliedSteering.toFixed(2);
}

function setCapturePending(pending) {
  state.capturePending = !!pending;
  const btn = document.getElementById("captureOnceBtn");
  if (!btn) return;
  btn.disabled = state.capturePending;
  btn.classList.toggle("pending", state.capturePending);
  const title = btn.querySelector(".capture-once-title");
  const subtitle = btn.querySelector(".capture-once-subtitle");
  if (title) title.textContent = state.capturePending ? "SNAPPING…" : "SNAPSHOT";
  if (subtitle) subtitle.textContent = state.capturePending ? "Saving current frame" : "Save one frame";
}

function findSelectedSession() {
  return state.sessions.find((item) => item.name === state.selectedSession) || null;
}

function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function updateSessionExportUi() {
  const select = document.getElementById("sessionSelect");
  const downloadBtn = document.getElementById("downloadSessionBtn");
  if (select) {
    const names = new Set((state.sessions || []).map((item) => item.name));
    if (!state.selectedSession || !names.has(state.selectedSession)) {
      state.selectedSession = state.sessions?.[0]?.name || "";
    }
    select.innerHTML = "";
    if (!state.sessions.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No recorded sessions yet";
      select.appendChild(opt);
    } else {
      state.sessions.forEach((item) => {
        const opt = document.createElement("option");
        opt.value = item.name;
        opt.textContent = item.name;
        if (item.name === state.selectedSession) opt.selected = true;
        select.appendChild(opt);
      });
    }
  }
  const session = findSelectedSession();
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };
  setText("sessionImageCount", session ? String(session.image_count ?? 0) : "0");
  setText("sessionUpdatedAt", session ? formatDateTime(session.updated_at) : "--");
  setText("sessionPath", session ? (session.path || `records/${session.name}`) : "records");
  if (downloadBtn) downloadBtn.disabled = !session;
}

async function refreshSessions(preserveSelection = true) {
  const currentSelection = preserveSelection ? state.selectedSession : "";
  const data = await fetchJson("/api/record/sessions");
  state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
  state.selectedSession = currentSelection && state.sessions.some((item) => item.name === currentSelection)
    ? currentSelection
    : (state.sessions[0]?.name || "");
  updateSessionExportUi();
  return data;
}

function updateSessionSelectionFromStatus(data) {
  const candidate = String(data?.record_session_name || "").trim();
  if (!candidate) return;
  if ((state.sessions || []).some((item) => item.name === candidate)) {
    state.selectedSession = candidate;
    updateSessionExportUi();
  }
}

function downloadSelectedSession() {
  const session = findSelectedSession();
  if (!session) {
    setBanner("sessionExportMessage", "No session selected.", "muted");
    return;
  }
  const url = `/api/record/download?session=${encodeURIComponent(session.name)}`;
  const link = document.createElement("a");
  link.href = url;
  link.download = `${session.name}.zip`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setBanner("sessionExportMessage", `Downloading ${session.name}.zip`, "muted");
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
  setText("recordSessionName", data.record_session_name || "none");
  setText("recordSavePath", data.record_save_path || data.snapshot_save_path || "records");
  setText("recordElapsed", formatElapsed(data.record_elapsed_seconds || 0));
  setText("recordLastSave", data.record_last_saved || data.snapshot_last_saved || "none");

  const previewMeta = document.getElementById("cameraPreviewMeta");
  if (previewMeta) {
    const extraError = data.camera_error ? ` · ${data.camera_error}` : "";
    previewMeta.textContent = `Backend: ${data.camera_backend || "unknown"} · ${previewState} preview${extraError}`;
  }

  setRecordToggle(!!data.recording, false);
  updateOverlayVisuals(data);
  updateSessionSelectionFromStatus(data);

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
    await refreshSessions(true);
    await pollStatus();
  } catch (error) {
    setRecordToggle(!next, false);
    throw error;
  }
}

async function captureOneShot() {
  setCapturePending(true);
  try {
    const data = await fetchJson("/api/record/capture_once", { method: "POST" });
    triggerSnapshotFlash();
    setBanner("statusBanner", data.message || "Snapshot saved.", "muted");
    if (data && data.state) updateStatusUi(data.state);
    await refreshSessions(true);
    return data;
  } finally {
    setCapturePending(false);
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
  state.rawTargetSteering = clamp(Number(steering || 0), -1, 1);
  state.rawTargetThrottle = clamp(Number(throttle || 0), -1, 1);
  updateDerivedTargets();
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
  const throttle = (0.5 - ny) * 2;
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
    state.rawTargetSteering = clamp(state.rawTargetSteering + horizontal * STEP_SIZE, -1, 1);
  } else {
    state.rawTargetSteering = moveTowards(state.rawTargetSteering, 0, STEP_SIZE);
  }

  if (vertical !== 0) {
    state.rawTargetThrottle = clamp(state.rawTargetThrottle + vertical * STEP_SIZE, -1, 1);
  } else {
    state.rawTargetThrottle = moveTowards(state.rawTargetThrottle, 0, STEP_SIZE);
  }

  updateDerivedTargets();
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

  const nextSteer = moveTowards(state.manualSteering, state.targetSteering, state.steerRate);
  const nextThrottle = moveTowards(
    state.manualThrottle,
    state.targetThrottle,
    Math.min(state.throttleRate, Math.max(state.maxThrottle, state.throttleRate))
  );
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
    updateDerivedTargets();
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

  [
    ["steerCurve", (value) => { state.steerCurve = Number(value) / 100; }],
    ["throttleCurve", (value) => { state.throttleCurve = Number(value) / 100; }],
    ["steerRate", (value) => { state.steerRate = Number(value) / 100; }],
    ["throttleRate", (value) => { state.throttleRate = Number(value) / 100; }],
  ].forEach(([id, apply]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("input", (event) => {
      apply(event.target.value);
      updateDerivedTargets();
      updateRangeText();
      applyManualState();
      saveManualFeel();
    });
  });

  document.getElementById("captureOnceBtn").addEventListener("click", async () => {
    try {
      await captureOneShot();
    } catch (error) {
      setBanner("statusBanner", error.message, "muted");
    }
  });

  document.getElementById("recordToggleBtn").addEventListener("click", async () => {
    try {
      await toggleRecording();
    } catch (error) {
      setBanner("statusBanner", error.message, "muted");
    }
  });

  document.getElementById("sessionSelect")?.addEventListener("change", (event) => {
    state.selectedSession = event.target?.value || "";
    updateSessionExportUi();
  });

  document.getElementById("refreshSessionsBtn")?.addEventListener("click", async () => {
    try {
      await refreshSessions(true);
      setBanner("sessionExportMessage", "Session list refreshed.", "muted");
    } catch (error) {
      setBanner("sessionExportMessage", error.message, "muted");
    }
  });

  document.getElementById("downloadSessionBtn")?.addEventListener("click", () => {
    downloadSelectedSession();
  });

  document.getElementById("overlayToggleBtn").addEventListener("click", () => {
    const nextMode = (state.overlayMode + 1) % 3;
    setOverlayMode(nextMode);
    const message = nextMode === 0
      ? "Frame overlay off."
      : nextMode === 1
        ? "Overlay 1: throttle and steering enabled."
        : "Overlay 2 placeholder enabled.";
    setBanner("statusBanner", message, "muted");
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

  updateDerivedTargets();
  updateRangeText();
  const desiredPage = data.current_page || state.page || "manual";
  if (desiredPage !== state.page && defaultLayouts[desiredPage]) {
    renderActivePage(desiredPage);
  }
}

async function init() {
  loadManualFeel();
  updateDerivedTargets();
  renderActivePage(state.page);
  updateRangeText();
  setCapturePending(false);
  setOverlayMode(0);
  setupDocking();
  setupManualControls();
  setupEvents();
  await refreshModels();
  await refreshSessions(false);
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
