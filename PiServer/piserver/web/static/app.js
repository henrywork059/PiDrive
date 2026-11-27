const gridCols = 45;
const gridRows = 25;
const layoutKeyPrefix = "PiServerLayout:v0_3_21:";
const manualFeelKey = "PiServerManualFeel:v0_3_5";
const styleSettingsFields = [
  { id: "styleBg", cssVar: "--bg", type: "color" },
  { id: "stylePanel", cssVar: "--panel", type: "color" },
  { id: "stylePanelAlt", cssVar: "--panel-alt", type: "color" },
  { id: "styleText", cssVar: "--text", type: "color" },
  { id: "styleMuted", cssVar: "--muted", type: "color" },
  { id: "styleAccent", cssVar: "--accent", type: "color" },
  { id: "styleDanger", cssVar: "--danger", type: "color" },
  { id: "styleWarn", cssVar: "--warn", type: "color" },
  { id: "styleOk", cssVar: "--ok", type: "color" },
  { id: "styleFontScale", cssVar: "--font-scale", type: "range", unit: "%", fallback: 80 },
  { id: "styleWorkspacePad", cssVar: "--workspace-pad", type: "range", unit: "px", fallback: 10 },
  { id: "styleGap", cssVar: "--gap", type: "range", unit: "px", fallback: 4 },
  { id: "styleRadius", cssVar: "--radius", type: "range", unit: "px", fallback: 10 },
  { id: "styleControlRadius", cssVar: "--control-radius", type: "range", unit: "px", fallback: 12 },
  { id: "styleCardRadius", cssVar: "--card-radius", type: "range", unit: "px", fallback: 14 },
  { id: "stylePanelPad", cssVar: "--panel-pad", type: "range", unit: "px", fallback: 12 },
  { id: "styleHeaderPadY", cssVar: "--panel-head-pad-y", type: "range", unit: "px", fallback: 10 },
  { id: "styleHeaderPadX", cssVar: "--panel-head-pad-x", type: "range", unit: "px", fallback: 12 },
  { id: "styleCardGap", cssVar: "--card-gap", type: "range", unit: "px", fallback: 10 },
  { id: "styleFieldGap", cssVar: "--field-gap", type: "range", unit: "px", fallback: 10 },
];
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
    status: { c: 1, r: 1, w: 7, h: 14 },
    estop: { c: 1, r: 15, w: 7, h: 4 },
    record: { c: 1, r: 19, w: 7, h: 4 },
    viewer: { c: 8, r: 1, w: 20, h: 22 },
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
  layoutPreview: null,
  latestStatus: null,
  statusTimer: null,
  statusInFlight: false,
  statusPollingReady: false,
  statusFailures: 0,
  statusVerified: false,
  statusRevision: 0,
  modelListRevision: 0,
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
  sessionListRevision: 0,
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



function normalizeHexColor(value, fallback = "#000000") { return window.PiServerOperatorFormat.normalizeHexColor(value, fallback); }
function hexToRgbTriplet(value) { return window.PiServerOperatorFormat.hexToRgbTriplet(value); }
function parseNumericStyleValue(value, fallback = 0) { return window.PiServerOperatorFormat.parseNumericStyleValue(value, fallback); }

function styleManager() {
  return window.PiServerStyle || null;
}

function readResolvedStyleVars() {
  return styleManager()?.getResolvedVars?.() || {};
}

function collectStyleOverridesFromInputs() {
  const overrides = {};
  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    const value = field.type === "range"
      ? `${el.value}${field.unit || ""}`
      : normalizeHexColor(el.value);
    overrides[field.cssVar] = value;
    if (field.cssVar === "--accent") overrides["--accent-rgb"] = hexToRgbTriplet(value);
    if (field.cssVar === "--font-scale") overrides["--font-scale-factor"] = String(Number(el.value) / 100);
  });
  return overrides;
}

function applyStyleOverridesToPage(overrides) {
  styleManager()?.saveCustomOverrides?.(overrides);
}

// Derive the visible and accessible value from the same native, clamped input.
function updateStyleRangeReadout(field, el) {
  const value = el.value;
  const unit = field.unit || "";
  const valueEl = document.getElementById(`${field.id}Value`);
  if (valueEl) valueEl.textContent = `${value}${unit}`;
  const spokenUnit = unit === "%" ? " percent" : unit === "px" ? " pixels" : unit ? " " + unit : "";
  el.setAttribute("aria-valuetext", value + spokenUnit);
}

function syncStyleInputsFromCurrentVars() {
  const resolved = readResolvedStyleVars();
  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    const raw = resolved[field.cssVar];
    if (field.type === "range") {
      const numeric = parseNumericStyleValue(raw, field.fallback || Number(el.min || 0));
      el.value = `${numeric}`;
      updateStyleRangeReadout(field, el);
    } else {
      el.value = normalizeHexColor(raw, el.value || "#000000");
    }
  });
}

function syncStyleValueLabelsFromInputs() {
  styleSettingsFields.forEach((field) => {
    if (field.type !== "range") return;
    const el = document.getElementById(field.id);
    if (el) updateStyleRangeReadout(field, el);
  });
}

function previewStyleOverridesFromInputs() {
  const manager = styleManager();
  manager?.applyTheme?.(manager.getCurrentTheme?.());
  const root = document.documentElement;
  Object.entries(collectStyleOverridesFromInputs()).forEach(([key, value]) => {
    root.style.setProperty(key, value);
  });
  syncStyleValueLabelsFromInputs();
}

function openStyleSettings() {
  const modal = document.getElementById("styleSettingsModal");
  if (!modal) return;
  syncStyleInputsFromCurrentVars();
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
  document.getElementById("closeStyleSettingsBtn")?.focus();
}

function closeStyleSettings() {
  const modal = document.getElementById("styleSettingsModal");
  if (!modal) return;
  const manager = styleManager();
  manager?.applyTheme?.(manager.getCurrentTheme?.());
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
  document.getElementById("openStyleSettingsBtn")?.focus();
}

function resetStyleSettings() {
  styleManager()?.resetCustomOverrides?.();
  syncStyleInputsFromCurrentVars();
}

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

function shortLastSaveLabel(value) { return window.PiServerOperatorFormat.shortLastSaveLabel(value); }
function formatElapsed(totalSeconds) { return window.PiServerOperatorFormat.formatElapsed(totalSeconds); }

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
  return window.PiServerLayout.clone(layout);
}

function loadLayout(page) {
  const defaults = defaultLayouts[page] || defaultLayouts.manual;
  try {
    return window.PiServerLayout.merge(defaults, localStorage.getItem(layoutStorageKey(page)));
  } catch {
    return deepCloneLayout(defaults);
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

function applyLayoutBoxes(layout) {
  panelEls().forEach((panel) => {
    const id = panel.dataset.panel;
    const box = layout[id];
    if (!box) return;
    setPanelBox(panel, box);
  });
}

function applyLayout(page) {
  applyLayoutBoxes(loadLayout(page));
}

function updateLayoutPreviewControls() {
  const preset = window.PiServerLayout.preset(state.page);
  const preview = document.getElementById("previewLayoutBtn");
  const cancel = document.getElementById("cancelLayoutPreviewBtn");
  const reset = document.getElementById("resetLayoutBtn");
  if (preview) {
    preview.disabled = !preset || !!state.layoutPreview;
    preview.textContent = preset ? `Preview ${preset.name} layout` : "No preset for this workspace";
  }
  if (cancel) cancel.hidden = !state.layoutPreview;
  if (reset) reset.disabled = !!state.layoutPreview;
  renderLayoutPreviewDiagram(state.layoutPreview);
  const feedback = document.getElementById("layoutPreviewMessage");
  if (feedback) feedback.textContent = state.layoutPreview
    ? "Unsaved preview — Save layout to keep, or Cancel."
    : "Layout controls affect this browser only.";
}

function renderLayoutPreviewDiagram(draft) {
  const diagram = document.getElementById("layoutPreviewDiagram");
  if (!diagram) return;
  diagram.replaceChildren();
  diagram.hidden = !draft;
  if (!draft) return;
  const labels = {status:"Status",estop:"STOP",viewer:"Preview",manual:"Drive",runtime:"Tuning",record:"Record",camera:"Camera",model:"Model"};
  diagram.setAttribute("aria-label", draft.name + " desktop layout preview: " +
    Object.keys(draft.candidate).map(key => labels[key] || key).join(", "));
  for (const [key, box] of Object.entries(draft.candidate)) {
    const panel = document.createElement("span");
    panel.textContent = labels[key] || key;
    panel.style.gridColumn = box.c + " / span " + box.w;
    panel.style.gridRow = box.r + " / span " + box.h;
    diagram.appendChild(panel);
  }
}

function previewWorkspaceLayout() {
  if (state.layoutPreview || state.dragging || state.resizing) return;
  const draft = window.PiServerLayout.begin(state.page, currentLayout());
  if (!draft) return;
  const preview = document.getElementById("previewLayoutBtn");
  const restoreFocus = document.activeElement === preview;
  state.layoutPreview = draft;
  applyLayoutBoxes(draft.candidate);
  updateLayoutPreviewControls();
  if (restoreFocus) document.getElementById("cancelLayoutPreviewBtn")?.focus();
  window.requestAnimationFrame(updateManualPadSizing);
}

function cancelWorkspaceLayout() {
  const draft = state.layoutPreview;
  if (!draft) return;
  const cancel = document.getElementById("cancelLayoutPreviewBtn");
  const restoreFocus = document.activeElement === cancel;
  if (draft.page === state.page) applyLayoutBoxes(draft.original);
  state.layoutPreview = null;
  updateLayoutPreviewControls();
  if (restoreFocus) {
    const preview = document.getElementById("previewLayoutBtn");
    if (preview && !preview.disabled) preview.focus();
  }
  window.requestAnimationFrame(updateManualPadSizing);
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
  const stacked = window.matchMedia("(max-width: 1080px)");
  // Register once regardless of the initial viewport. A breakpoint change or
  // cancelled pointer must restore the pre-gesture box, never save a partial drag.
  function cancelDocking() {
    for (const [key, className] of [["dragging", "dragging"], ["resizing", "resizing"]]) {
      const gesture = state[key];
      if (!gesture) continue;
      setPanelBox(gesture.panel, gesture.box);
      gesture.panel.classList.remove(className);
      state[key] = null;
    }
  }
  stacked.addEventListener("change", () => { if (stacked.matches) cancelDocking(); });
  window.addEventListener("pointercancel", cancelDocking);

  panelEls().forEach((panel) => {
    const head = panel.querySelector(".panel-head");
    const handle = panel.querySelector(".resize-handle");
    if (!head || !handle) return;

    head.addEventListener("pointerdown", (event) => {
      if (stacked.matches || state.layoutPreview || event.target.closest("button, select, input, label")) return;
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
      if (stacked.matches || state.layoutPreview) return;
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
    if (stacked.matches) { cancelDocking(); return; }
    if (state.dragging) {
      const { rect, cellW, cellH } = workspaceMetrics();
      const col = Math.round((event.clientX - rect.left - state.dragging.offsetX) / cellW) + 1;
      const row = Math.round((event.clientY - rect.top - state.dragging.offsetY) / cellH) + 1;
      const box = window.PiServerLayout.moveBox(state.dragging.box, col, row, gridCols, gridRows);
      setPanelBox(state.dragging.panel, box);
    }

    if (state.resizing) {
      const dx = event.clientX - state.resizing.startX;
      const dy = event.clientY - state.resizing.startY;
      const dw = Math.round(dx / state.resizing.cellW);
      const dh = Math.round(dy / state.resizing.cellH);
      const box = window.PiServerLayout.resizeBox(state.resizing.box, dw, dh, gridCols, gridRows);
      setPanelBox(state.resizing.panel, box);
    }
  });

  window.addEventListener("pointerup", () => {
    if (stacked.matches) { cancelDocking(); return; }
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
  if (state.layoutPreview && state.layoutPreview.page !== page) cancelWorkspaceLayout();
  state.page = page;
  document.body.dataset.page = page;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
    btn.setAttribute("aria-pressed", String(btn.dataset.page === page));
  });
  const visible = new Set(pagePanels[page] || pagePanels.manual);
  panelEls().forEach((panel) => {
    panel.classList.toggle("panel-hidden", !visible.has(panel.dataset.panel));
  });
  if (state.layoutPreview) applyLayoutBoxes(state.layoutPreview.candidate);
  else applyLayout(page);
  updateLayoutPreviewControls();
  window.requestAnimationFrame(updateManualPadSizing);
}

let csrfTokenPromise = null;

async function getCsrfToken() {
  if (!csrfTokenPromise) {
    csrfTokenPromise = fetch("/api/auth/csrf", { credentials: "same-origin", cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) {
          if (response.status === 401) window.location.assign("/login");
          throw new Error("Access expired. Reload the page to sign in again.");
        }
        const data = await response.json();
        return String(data.csrf_token || "");
      })
      .catch((error) => {
        csrfTokenPromise = null;
        throw error;
      });
  }
  return csrfTokenPromise;
}

// R47: show only server-issued trace metadata, never request bodies or paths.
function tracedRequestError(payload, status, url, fallback) {
  const traceId = String(payload?.correlation_id || '');
  if (!/^[0-9a-f]{16}$/.test(traceId)) {
    return new Error(payload?.message || payload?.error || fallback);
  }
  const actions = {
    '/api/motor/apply': 'Motor Apply failed. Check the settings, then retry.',
    '/api/camera/apply': 'Camera Apply failed. Check the camera, then retry.',
    '/api/model/load': 'Model load failed. Check the model, then retry.',
    '/api/model/upload': 'Model upload failed. Choose a .tflite file, then retry.',
  };
  const error = new Error(status === 403 || status === 401
    ? fallback : (actions[url] || 'Pi request failed. Check Pi status, then retry.'));
  error.trace = {
    id: traceId,
    operation: /^[a-zA-Z0-9_.-]{1,64}$/.test(String(payload?.operation || ''))
      ? payload.operation : 'unknown',
    status: Number(status) || 0,
    code: /^[A-Z0-9_-]{1,48}$/.test(String(payload?.code || ''))
      ? payload.code : '',
  };
  return error;
}

function appendRequestTrace(id, error) {
  const target = document.getElementById(id);
  if (!target || !error?.trace?.id) return;
  const details = document.createElement('details');
  const title = document.createElement('summary');
  title.textContent = 'Error details';
  const data = document.createElement('span');
  const trace = error.trace;
  data.textContent = ' Ref ' + trace.id + ' · ' + trace.operation +
    ' · HTTP ' + trace.status + (trace.code ? ' · ' + trace.code : '');
  details.appendChild(title);
  details.appendChild(data);
  target.appendChild(details);
}

// UX75: read-only requests must not hang dashboard startup or permanently
// hold the single in-flight status poll. Do not abort control/STOP/Save POSTs:
// their completion is independently confirmed by server-side acknowledgments.
const READ_ONLY_TIMEOUT_MS = 3500;

async function fetchJson(url, options = {}) {
  const requestOptions = { ...options, credentials: "same-origin" };
  const method = String(requestOptions.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = await getCsrfToken();
    if (csrfToken) {
      requestOptions.headers = { ...options.headers, "X-PiServer-CSRF": csrfToken };
    }
  }
  const controller = method === "GET" && !requestOptions.signal ? new AbortController() : null;
  let timeoutId = null;
  if (controller) {
    requestOptions.signal = controller.signal;
    timeoutId = setTimeout(() => controller.abort(), READ_ONLY_TIMEOUT_MS);
  }
  try {
    const response = await fetch(url, requestOptions);
    const data = await response.json();
    if (!response.ok || data?.ok === false || (data?.saved === false && !["GET", "HEAD"].includes(method))) {
      if (response.status === 401) {
        window.location.assign("/login");
      }
      const nextStep = response.status === 403 ? "Permission denied. Sign in with an authorized account."
        : response.status === 401 ? "Session expired. Sign in again."
        : response.status >= 500 ? "PiServer unavailable. Check the connection, then retry."
        : `Request failed (${response.status}). Check the inputs and retry.`;
      throw tracedRequestError(data, response.status, url, nextStep);
    }
    return data;
  } catch (error) {
    if (controller?.signal.aborted) {
      throw new Error("PiServer read-only request timed out. Check the connection, then retry.");
    }
    throw error;
  } finally {
    if (timeoutId !== null) clearTimeout(timeoutId);
  }
}

function setBanner(id, text, tone = "muted") {
  const el = document.getElementById(id);
  if (!el) return;
  if (el.textContent !== text) el.textContent = text;
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
  // Announce the normalized readout, not the integer slider encoding.
  for (const id of ["maxThrottle", "steerMix", "steerBias", "steerCurve", "throttleCurve",
                    "steerRate", "throttleRate", "leftMaxSpeed", "rightMaxSpeed"]) {
    const input = document.getElementById(id);
    const readout = document.getElementById(id + "Value");
    if (input && readout) input.setAttribute("aria-valuetext", readout.textContent.replace("×", " times"));
  }
}

function updateToolbarBadge(status) {
  const badge = document.getElementById("maintenanceBadge");
  if (!badge) return;
  const stopped = !!(status && status.safety_stop);
  badge.textContent = stopped ? "e-stop" : "run";
  badge.classList.remove("unknown");
  badge.classList.toggle("on", stopped);
  badge.classList.toggle("off", !stopped);
}

function setEstopToggle(enabled) {
  state.estopEnabled = !!enabled;
  const btn = document.getElementById("estopToggle");
  if (!btn) return;
  btn.classList.toggle("on", state.estopEnabled);
  btn.classList.toggle("off", !state.estopEnabled);
  btn.removeAttribute("data-status");
  btn.setAttribute("aria-pressed", state.estopEnabled ? "true" : "false");
  const title = btn.querySelector(".estop-toggle-title");
  const subtitle = btn.querySelector(".estop-toggle-subtitle");
  if (title) title.textContent = state.estopEnabled ? "E-STOP ACTIVE" : "E-STOP OFF";
  if (subtitle) subtitle.textContent = state.estopEnabled ? "Output locked at zero" : "Tap to engage";
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
  if (title) title.textContent = state.recordEnabled ? "RECORD ON" : "RECORD OFF";
  if (subtitle) subtitle.textContent = state.recordPending
    ? (state.recordEnabled ? "Starting capture…" : "Stopping capture…")
    : (state.recordEnabled ? "Tap to stop capture" : "Tap to start capture");
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
        ? "Throttle + steer"
        : normalized === 2
          ? "Arc path"
          : "Cycle view";
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
  const overlayTwoSvg = document.getElementById("overlayTwoSvg");
  const overlayTwoTrack = document.getElementById("overlayTwoTrack");
  const overlayTwoArc = document.getElementById("overlayTwoArc");
  const overlayTwoPointStartRing = document.getElementById("overlayTwoPointStartRing");
  const overlayTwoPointStart = document.getElementById("overlayTwoPointStart");
  const overlayTwoPointEndRing = document.getElementById("overlayTwoPointEndRing");
  const overlayTwoPointEnd = document.getElementById("overlayTwoPointEnd");
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

  if (overlayTwoSvg && overlayTwoTrack && overlayTwoArc && overlayTwoPointStartRing && overlayTwoPointStart && overlayTwoPointEndRing && overlayTwoPointEnd) {
    const shouldShowPath = throttleNorm > 0;
    overlayTwoSvg.classList.toggle("has-path", shouldShowPath);
    if (shouldShowPath) {
      const startX = 50;
      const startY = 92;
      const verticalTravel = 18 + (throttleNorm * 54);
      const endY = clamp(startY - verticalTravel, 18, 92);
      const horizontalReach = 12 + (throttleNorm * 22);
      const endX = clamp(startX + (steerNorm * horizontalReach), 18, 82);
      const dx = endX - startX;
      const dy = startY - endY;
      const cp1x = startX;
      const cp1y = startY - Math.max(8, dy * 0.62);
      const cp2x = startX + dx * 0.72;
      const cp2y = endY;
      const d = `M ${startX} ${startY} C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${endX} ${endY}`;
      overlayTwoTrack.setAttribute("d", d);
      overlayTwoArc.setAttribute("d", d);
      [overlayTwoPointStartRing, overlayTwoPointStart].forEach((el) => {
        el.setAttribute("cx", `${startX}`);
        el.setAttribute("cy", `${startY}`);
      });
      [overlayTwoPointEndRing, overlayTwoPointEnd].forEach((el) => {
        el.setAttribute("cx", `${endX}`);
        el.setAttribute("cy", `${endY}`);
      });
    } else {
      overlayTwoTrack.setAttribute("d", "");
      overlayTwoArc.setAttribute("d", "");
      [overlayTwoPointStartRing, overlayTwoPointStart, overlayTwoPointEndRing, overlayTwoPointEnd].forEach((el) => {
        el.setAttribute("cx", "50");
        el.setAttribute("cy", "92");
      });
    }
  }
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

function getSelectedSessionLabel(session) {
  if (!session) return "folder";
  return session.kind === "snapshots" ? "snapshot folder" : "session folder";
}

function formatDateTime(value) { return window.PiServerOperatorFormat.formatDateTime(value); }

function updateSessionExportUi() {
  const select = document.getElementById("sessionSelect");
  const downloadBtn = document.getElementById("downloadSessionBtn");
  const deleteBtn = document.getElementById("deleteSessionBtn");
  if (select) {
    const names = new Set((state.sessions || []).map((item) => item.name));
    if (!state.selectedSession || !names.has(state.selectedSession)) {
      state.selectedSession = state.sessions?.[0]?.name || "";
    }
    select.innerHTML = "";
    if (!state.sessions.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No saved folders — record or capture a frame";
      select.appendChild(opt);
    } else {
      state.sessions.forEach((item) => {
        const opt = document.createElement("option");
        opt.value = item.name;
        const kindLabel = item.kind === "snapshots" ? "snapshot folder" : "session";
        opt.textContent = `${item.name} · ${kindLabel}`;
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
  setText("sessionKind", session ? (session.label || getSelectedSessionLabel(session)) : "--");
  setText("sessionImageCount", session ? String(session.image_count ?? 0) : "0");
  setText("sessionUpdatedAt", session ? formatDateTime(session.updated_at) : "--");
  setText("sessionPath", session ? (session.path || `records/${session.name}`) : "records");
  if (downloadBtn) downloadBtn.disabled = !session;
  if (deleteBtn) deleteBtn.disabled = !session || window.PiDriveDestructive.busy(deleteBtn);
}

async function refreshSessions(preserveSelection = true) {
  const revision = ++state.sessionListRevision;
  const initialSelection = state.selectedSession;
  let data;
  try {
    data = await fetchJson("/api/record/sessions");
  } catch (error) {
    if (revision !== state.sessionListRevision) return null;
    throw error;
  }
  if (revision !== state.sessionListRevision) return null;
  // Read the selection when the list arrives, not when the GET starts.
  const currentSelection = preserveSelection || state.selectedSession !== initialSelection
    ? state.selectedSession : "";
  state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
  state.selectedSession = currentSelection && state.sessions.some((item) => item.name === currentSelection)
    ? currentSelection
    : (state.sessions[0]?.name || "");
  updateSessionExportUi();
  return data;
}

async function refreshSessionsWithFeedback() {
  try {
    if (await refreshSessions(true)) {
      setBanner("sessionExportMessage", "Session list refreshed.", "muted");
    }
  } catch (error) {
    setBanner("sessionExportMessage", error.message, "muted");
  }
}

function updateSessionSelectionFromStatus(data) {
  const candidate = String(data?.record_session_name || "").trim();
  if (!candidate) return;
  const current = findSelectedSession();
  if (current) return;
  if ((state.sessions || []).some((item) => item.name === candidate)) {
    state.selectedSession = candidate;
    updateSessionExportUi();
  }
}

function downloadSelectedSession() {
  const session = findSelectedSession();
  if (!session) {
    setBanner("sessionExportMessage", "Record or capture a frame, then Refresh folders.", "muted");
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

async function deleteSelectedSession() {
  const button = document.getElementById('deleteSessionBtn');
  if (window.PiDriveDestructive.busy(button)) return;
  const session = findSelectedSession();
  if (!session) {
    setBanner("sessionExportMessage", "Record or capture a frame, then Refresh folders.", "muted");
    return;
  }
  const label = getSelectedSessionLabel(session);
  const ok = await window.PiDriveDestructive.confirm(button, `Permanently delete ${label}: ${session.name}?\n\n${session.image_count ?? 'Unknown number of'} images. This removes the named folder from the Pi and cannot be undone.`);
  if (!ok) return;
  try {
  const data = await fetchJson("/api/record/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session: session.name, confirm: true })
  });
  // The acknowledged deletion provides a newer authoritative folder list.
  // Ignore every GET started before this acknowledgement, including errors.
  ++state.sessionListRevision;
  state.sessions = Array.isArray(data.sessions) ? data.sessions : [];
  state.selectedSession = state.sessions.some((item) => item.name === state.selectedSession)
    ? state.selectedSession
    : (state.sessions[0]?.name || "");
  updateSessionExportUi();
  if (data && data.state) updateStatusUi(data.state);
  setBanner("sessionExportMessage", data.message || `Deleted ${session.name}.`, "muted");
  } finally { window.PiDriveDestructive.finish(button); updateSessionExportUi(); }
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

// UX75 / R35: a failed status read cannot prove E-STOP is off or on.
// Keep the last confirmed server-side state internally, but do not present
// cached telemetry as live. The E-STOP control remains available to request
// STOP; rearm is forbidden until fresh status succeeds.
function markStatusUnverified(error) {
  state.statusVerified = false;
  const badge = document.getElementById("maintenanceBadge");
  if (badge) {
    badge.textContent = "offline";
    badge.classList.remove("on", "off");
    badge.classList.add("unknown");
  }
  const panelState = document.querySelector('.dock-panel[data-panel="status"] .panel-mini');
  if (panelState) panelState.textContent = "offline";
  const toggle = document.getElementById("estopToggle");
  if (toggle) {
    toggle.setAttribute("data-status", "unknown");
    toggle.setAttribute("aria-pressed", "mixed");
    const title = toggle.querySelector(".estop-toggle-title");
    const subtitle = toggle.querySelector(".estop-toggle-subtitle");
    if (title) title.textContent = "E-STOP STATUS UNKNOWN";
    if (subtitle) subtitle.textContent = "Request STOP · rearm unavailable";
  }
  for (const id of ["metricDriveState", "metricApplied", "metricWheels"]) {
    const metric = document.getElementById(id);
    if (metric) metric.textContent = "Unverified";
  }
  const message = error?.message || "PiServer status unavailable. Check the connection.";
  setBanner("statusBanner", `${message} Live state unverified; STOP can be requested, never assumed.`, "muted");
  const banner = document.getElementById("statusBanner");
  if (banner) banner.title = "Last telemetry is not current. Motor and safety state must be confirmed by the server.";
}

function updateStatusUi(data) {
  state.statusRevision += 1;
  state.latestStatus = data;
  state.statusVerified = true;
  const panelState = document.querySelector('.dock-panel[data-panel="status"] .panel-mini');
  if (panelState) panelState.textContent = "live";
  setEstopToggle(!!data.safety_stop);

  const driveState = data.safety_stop ? "E-stop active"
    : data.manual_command_timed_out ? "Manual command expired · stopped"
    : (data.active_algorithm === "manual" ? "Manual ready" : `${data.active_algorithm || "auto"} active`);
  previewHealth.setBackendLive(!!data.camera_preview_live);
  const errorText = data.camera_error ? String(data.camera_error) : "none";

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setText("metricDriveState", driveState);
  setText("metricApplied", `S ${Number(data.applied_steering || 0).toFixed(2)} · T ${Number(data.applied_throttle || 0).toFixed(2)}`);
  setText("metricManual", `S ${Number(state.targetSteering || 0).toFixed(2)} · T ${Number(state.targetThrottle || 0).toFixed(2)}`);
  const lastSaveRaw = data.record_last_saved || data.snapshot_last_saved || "none";
  setText("metricLastSave", shortLastSaveLabel(lastSaveRaw));
  const metricLastSaveEl = document.getElementById("metricLastSave");
  if (metricLastSaveEl) metricLastSaveEl.title = lastSaveRaw;
  renderPreviewHealth();
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
  setText("recordElapsed", formatElapsed(data.record_elapsed_seconds || 0));
  setText("recordLastSave", lastSaveRaw);
  const recordLastSaveEl = document.getElementById("recordLastSave");
  if (recordLastSaveEl) recordLastSaveEl.title = lastSaveRaw;

  setRecordToggle(!!data.recording, false);
  updateOverlayVisuals(data);
  updateSessionSelectionFromStatus(data);

  updateToolbarBadge(data);
  setBanner("statusBanner", data.system_message || "Ready.", "muted");
  const recovery = document.getElementById("configRecoveryBanner");
  if (recovery && data.config_recovery) {
    recovery.textContent = data.config_recovery.warning || "";
    recovery.hidden = !recovery.textContent;
  }
  const statusBanner = document.getElementById("statusBanner");
  if (statusBanner) {
    const serverAt = Number(data.server_status_at_ms);
    statusBanner.title = Number.isFinite(serverAt) && serverAt > 0
      ? `Server status as of ${new Date(serverAt).toLocaleTimeString()} (server clock); updated by read-only polling.`
      : "Server status freshness timestamp unavailable.";
  }
}

// R43: read-only UI status is deliberately independent of the 60 ms motor
// control tick and server-side safety/watchdog. Only one request in flight.
function statusPollDelayMs() {
  if (document.hidden) return 5000; // no requests in hidden tabs
  const status = state.latestStatus || {};
  const active = !!(status.camera_preview_live || status.recording || status.ai_running ||
    Math.abs(state.manualThrottle) > 0.001 || Math.abs(state.manualSteering) > 0.001 ||
    state.pointerControl.active || Object.values(state.stepInputs).some(Boolean));
  const base = active ? 800 : 2500;
  return Math.min(8000, base * Math.pow(2, Math.min(state.statusFailures, 3)));
}

function scheduleStatusPoll(delayMs = statusPollDelayMs()) {
  if (state.statusTimer) clearTimeout(state.statusTimer);
  state.statusTimer = setTimeout(() => {
    state.statusTimer = null;
    void pollStatus();
  }, delayMs);
}

async function pollStatus() {
  if (document.hidden) {
    scheduleStatusPoll();
    return;
  }
  if (state.statusInFlight) return;
  state.statusInFlight = true;
  // A mutation acknowledgement may supply a newer confirmed snapshot while
  // this GET is pending. Never let an older request overwrite that snapshot.
  const revisionAtStart = state.statusRevision;
  try {
    const data = await fetchJson("/api/status");
    if (revisionAtStart !== state.statusRevision) return;
    state.statusFailures = 0;
    updateStatusUi(data);
    syncControlsFromStatus(data);
  } catch (error) {
    if (revisionAtStart !== state.statusRevision) return;
    state.statusFailures = Math.min(3, state.statusFailures + 1);
    markStatusUnverified(error);
  } finally {
    state.statusInFlight = false;
    scheduleStatusPoll();
  }
}

async function refreshModels(preserveSelection = false) {
  const revision = ++state.modelListRevision;
  let data;
  try {
    data = await fetchJson("/api/model/list");
  } catch (error) {
    if (revision !== state.modelListRevision) return;
    throw error;
  }
  if (revision !== state.modelListRevision) return;
  const select = document.getElementById("modelSelect");
  if (!select) return;
  const selected = preserveSelection ? select.value : "";
  select.innerHTML = "";
  if (!(data.models || []).length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No .tflite models — upload a model";
    select.appendChild(option);
    setBanner("modelMessage", "No models on Pi. Upload a .tflite model first.", "muted");
  }
  (data.models || []).forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    if (data.active === name) option.selected = true;
    select.appendChild(option);
  });
  if (selected && (data.models || []).includes(selected)) select.value = selected;
  if (preserveSelection && (data.models || []).length) {
    setBanner("modelMessage", "Model list refreshed.", "muted");
  }
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
  const sidecar = document.getElementById("modelManifestFile")?.files?.[0];
  if (sidecar) {
    if (sidecar.name !== file.name + ".manifest.json") {
      setBanner("modelMessage", "Choose the matching " + file.name + ".manifest.json.", "muted");
      return;
    }
    form.append("manifest", sidecar);
  }
  const data = await fetchJson("/api/model/upload", { method: "POST", body: form });
  setBanner("modelMessage", data.message || "Model uploaded.", "muted");
  const manifestInput = document.getElementById("modelManifestFile");
  if (manifestInput) manifestInput.value = "";
  if (input) input.value = "";
  await refreshModels();
}

async function loadSelectedModel() {
  const select = document.getElementById("modelSelect");
  const filename = select?.value || "";
  if (!filename) {
    setBanner("modelMessage", "No model selected. Upload a .tflite file or choose a listed model.", "muted");
    return;
  }
  const data = await fetchJson("/api/model/load", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename })
  });
  const spec = data.input_spec;
  const shapeLabel = spec ? ` · ${spec.width}×${spec.height} RGB · ${spec.dtype}` : "";
  const experiment = data.model_metadata?.manifest?.experiment;
  const provenance = experiment ? ` · Run ${experiment.run_id} · SHA-256 ${data.model_metadata.manifest.model_sha256} (supplied provenance)` : " · Experiment unknown";
  setBanner("modelMessage", `${data.message || "Model loaded."}${shapeLabel}${provenance}`, "muted");
  await pollStatus();
}

async function deleteSelectedModel() {
  const button = document.getElementById('deleteModelBtn');
  if (window.PiDriveDestructive.busy(button)) return;
  const select = document.getElementById("modelSelect");
  const filename = select?.value || "";
  if (!filename) {
    setBanner("modelMessage", "No model selected. Choose a listed model to delete.", "muted");
    return;
  }
  const ok = await window.PiDriveDestructive.confirm(button, `Permanently delete model: ${filename}?\n\nThe model and its associated manifest will be removed from the Pi. This cannot be undone.`);
  if (!ok) return;
  try {
  const data = await fetchJson("/api/model/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, confirm: true })
  });
  setBanner("modelMessage", data.message || `Deleted ${filename}.`, "muted");
  await refreshModels();
  await pollStatus();
  } finally { window.PiDriveDestructive.finish(button); }
}

async function refreshRecordedFolders() {
  try {
    await refreshSessions(true);
    return true;
  } catch (error) {
    setBanner("sessionExportMessage", `Cannot refresh folders: ${error.message}. Retry after reconnecting.`, "muted");
    return false;
  }
}

async function toggleRecording() {
  const next = !state.recordEnabled;
  setRecordToggle(next, true);
  let data;
  try {
    data = await fetchJson("/api/record/toggle", { method: "POST" });
  } catch (error) {
    setRecordToggle(!next, false);
    throw error;
  }
  setBanner("statusBanner", data.message || "Recording toggled.", "muted");
  if (data && data.state) updateStatusUi(data.state);
  else setRecordToggle(!!data.recording, false);
  // A failed optional read cannot undo an acknowledged recording command.
  const foldersRefreshed = await refreshRecordedFolders();
  await pollStatus();
  if (!foldersRefreshed) {
    setBanner("statusBanner", "Recording command acknowledged; folder refresh failed. Retry after reconnecting.", "muted");
  }
}

async function captureOneShot() {
  setCapturePending(true);
  try {
    const data = await fetchJson("/api/record/capture_once", { method: "POST" });
    triggerSnapshotFlash();
    setBanner("statusBanner", data.message || "Snapshot saved.", "muted");
    if (data && data.state) updateStatusUi(data.state);
    if (!await refreshRecordedFolders()) {
      setBanner("statusBanner", "Snapshot saved; folder refresh failed. Retry after reconnecting.", "muted");
    }
    return data;
  } finally {
    setCapturePending(false);
  }
}

async function setEstop(enabled) {
  if (!enabled && !window.confirm("Rearm motor controls at zero? The previous command will not resume.")) return;
  const data = await fetchJson("/api/system/estop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(enabled ? { enabled: true } : { enabled: false, confirm: true })
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

const settingsFeedback = {
  camera: window.PiDriveSettingsFeedback.createSettingsFeedback(),
  motor: window.PiDriveSettingsFeedback.createSettingsFeedback()
};
function renderSettingsFeedback(kind) {
  const info = settingsFeedback[kind].snapshot();
  const badge = document.getElementById(kind + 'ApplyState');
  const detail = document.getElementById(kind + 'ApplyDetail');
  const retry = document.getElementById(kind + 'RetryApply');
  const apply = document.getElementById(kind === 'camera' ? 'cameraApplyBtn' : 'motorApplyBtn');
  if (badge) {
    badge.textContent = info.phase;
    badge.dataset.state = info.phase.toLowerCase();
  }
  if (detail) detail.textContent = info.detail;
  if (retry) retry.hidden = !info.retry;
  if (apply) apply.disabled = info.busy;
}
function settingsChanged(kind) {
  settingsFeedback[kind].edit();
  renderSettingsFeedback(kind);
}
const settingsReadbackMatches = window.PiDriveSettingsFeedback.matchesSubset;
async function confirmedConfig(path, requested, response, kind) {
  if (response?.ok !== true || response?.saved !== true) {
    throw new Error(response?.message || kind + ' settings were not saved.');
  }
  const current = await fetchJson(path);
  if (current?.ok !== true || !current.config || !response.config) {
    throw new Error(kind + ' configuration readback failed.');
  }
  // Compare only submitted settings. Camera/motor telemetry can change
  // between responses even while the saved configuration stays identical.
  const accepted = Object.fromEntries(Object.keys(requested)
    .map(key => [key, response.config[key]]));
  if (!settingsReadbackMatches(accepted, current.config)) {
    throw new Error(kind + ' settings did not match backend readback.');
  }
  return current.config;
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
    auto_white_balance: !!document.getElementById("cameraAwb").checked,
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
  document.getElementById("cameraAwb").checked = Boolean(config.auto_white_balance ?? config.awb ?? true);
  document.getElementById("cameraExposureUs").value = config.exposure_us ?? 12000;
  document.getElementById("cameraAnalogueGain").value = config.analogue_gain ?? 1.0;
  document.getElementById("cameraExposureComp").value = config.exposure_compensation ?? 0;
  document.getElementById("cameraBrightness").value = config.brightness ?? 0;
  document.getElementById("cameraContrast").value = config.contrast ?? 1;
  document.getElementById("cameraSaturation").value = config.saturation ?? 1;
  document.getElementById("cameraSharpness").value = config.sharpness ?? 1;
  setCameraResolutionPreset();
  renderPreviewResourceProfile(config);
}

function renderPreviewResourceProfile(config = {}) {
  const profile = document.getElementById("cameraResourceProfile");
  const effective = document.getElementById("cameraResourceEffective");
  if (profile) profile.value = config.preview_resource_profile || "standard";
  if (effective) effective.textContent = `Effective: ${config.effective_preview_fps ?? config.preview_fps ?? 12} FPS / JPEG ${config.effective_preview_quality ?? config.preview_quality ?? 60}`;
}

async function applyPreviewResourceProfile() {
  const field = document.getElementById("cameraResourceProfile");
  const button = document.getElementById("cameraResourceApply");
  if (!field || !button || button.disabled) return;
  const selected = field.value;
  button.disabled = true;
  field.disabled = true;
  try {
    const data = await fetchJson("/api/camera/apply", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({preview_resource_profile: selected})
    });
    const actual = await fetchJson("/api/camera/config");
    state.cameraConfig = actual.config || {};
    renderPreviewResourceProfile(state.cameraConfig);
    const applied = state.cameraConfig.preview_resource_profile === selected;
    setBanner("cameraResourceMessage", applied && data.saved ? "Applied and saved."
      : (data.message || "Profile was not confirmed and saved."), "muted");
  } catch (error) {
    setBanner("cameraResourceMessage", error.message || "Preview profile request failed.", "muted");
  } finally {
    field.disabled = false;
    button.disabled = false;
  }
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
  const feedback = settingsFeedback.camera;
  const token = feedback.begin();
  if (token === null) return;
  renderSettingsFeedback('camera');
  const payload = readCameraForm();
  try {
    const data = await fetchJson("/api/camera/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const confirmed = await confirmedConfig('/api/camera/config', payload, data, 'Camera');
    if (feedback.snapshot().revision === token) {
      state.cameraConfig = confirmed;
      fillCameraForm(confirmed);
    }
    feedback.complete(token, true,
      settingsReadbackMatches(payload, confirmed)
        ? 'Camera runtime and saved settings confirmed by backend.'
        : 'Camera settings normalized by backend; effective values shown.');
    setBanner("cameraMessage", data.message || "Camera settings applied.", "muted");
    refreshVideoFeed();
    await pollStatus();
  } catch (error) {
    feedback.fail(token, error.message);
    setBanner("cameraMessage", error.message || "Camera settings failed.", "muted");
    appendRequestTrace("cameraMessage", error);
  } finally { renderSettingsFeedback('camera'); }
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
  const feedback = settingsFeedback.motor;
  const token = feedback.begin();
  if (token === null) return;
  renderSettingsFeedback('motor');
  const payload = readMotorForm();
  try {
    const data = await fetchJson("/api/motor/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const confirmed = await confirmedConfig('/api/motor/config', payload, data, 'Motor');
    if (feedback.snapshot().revision === token) {
      state.motorConfig = confirmed;
      fillMotorForm(confirmed, true);
    }
    feedback.complete(token, true,
      settingsReadbackMatches(payload, confirmed)
        ? 'Motor runtime and saved settings confirmed by backend.'
        : 'Motor settings normalized by backend; effective values shown.');
    setBanner("motorMessage", data.message || "Motor settings applied.", "muted");
    await pollStatus();
  } catch (error) {
    feedback.fail(token, error.message);
    setBanner("motorMessage", error.message || "Motor settings failed.", "muted");
    appendRequestTrace("motorMessage", error);
  } finally { renderSettingsFeedback('motor'); }
}

const previewHealth = window.PiDrivePreviewFreshness.createPreviewFreshness(() => performance.now());
function renderPreviewHealth() {
  const health = previewHealth.snapshot();
  const age = health.ageMs === null ? 'no frame' : `${(health.ageMs / 1000).toFixed(1)}s old`;
  const indicator = document.getElementById('previewHealth');
  if (indicator) {
    const className = `preview-health ${health.state.toLowerCase()}`;
    const text = `${health.state} · ${age}`;
    if (indicator.className !== className) indicator.className = className;
    if (indicator.textContent !== text) indicator.textContent = text;
  }
  const viewer = document.querySelector('.viewer-frame');
  if (viewer) viewer.classList.toggle('preview-is-stale', health.hasFrame && health.state !== 'Live');
  const metric = document.getElementById('metricPreview');
  if (metric && metric.textContent !== health.state) metric.textContent = health.state;
  const meta = document.getElementById('cameraPreviewMeta');
  const status = state.latestStatus || {};
  const metaText = `Backend: ${status.camera_backend || 'unknown'} · ${health.state} · ${age}${status.camera_error ? ' · ' + status.camera_error : ''}`;
  if (meta && meta.textContent !== metaText) meta.textContent = metaText;
}
function previewDelayMs() {
  const fps = Number(document.getElementById("cameraPreviewFps")?.value || state.cameraConfig?.preview_fps || 12);
  const effective = state.cameraConfig?.preview_resource_profile === "economy"
    ? Math.min(fps, state.cameraConfig.effective_preview_fps ?? 6) : fps;
  return clamp(Math.round(1000 / Math.max(1, effective)), 40, 500);
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
  previewHealth.setPaused(true);
  renderPreviewHealth();
  if (state.previewTimer) {
    clearTimeout(state.previewTimer);
    state.previewTimer = null;
  }
  if (clearImage && state.previewObjectUrl) {
    try { URL.revokeObjectURL(state.previewObjectUrl); } catch {}
    state.previewObjectUrl = null;
  }
}

function schedulePreviewFrame(immediate = false, delayMs = previewDelayMs()) {
  if (!state.previewActive) return;
  if (state.previewTimer) clearTimeout(state.previewTimer);
  state.previewTimer = setTimeout(requestPreviewFrame, immediate ? 0 : delayMs);
}

async function requestPreviewFrame() {
  if (!state.previewActive || document.hidden) return;
  if (state.previewInFlight) {
    schedulePreviewFrame(false);
    return;
  }
  state.previewInFlight = true;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch(`/api/camera/frame.jpg?t=${Date.now()}`, { cache: "no-store", signal: controller.signal });
    if (response.status === 204) throw new Error('No camera frame');
    if (!response.ok) throw new Error(`Preview request failed (${response.status})`);
    const live = response.headers.get('X-Preview-Live') === '1';
    const sequenceHeader = response.headers.get('X-Preview-Seq');
    const sequence = sequenceHeader === null ? NaN : Number(sequenceHeader);
    if (!Number.isSafeInteger(sequence) || sequence < 0) throw new Error('Invalid camera frame sequence');
    previewHealth.setBackendLive(live);
    if (!live || !previewHealth.isNew(sequence)) {
      if (!live || previewHealth.snapshot().ageMs >= 1500) previewHealth.fail();
      return;
    }
    const blob = await response.blob();
    if (!blob.size) throw new Error('Empty preview frame');
    const url = URL.createObjectURL(blob);
    try {
      const decoded = new Image();
      decoded.src = url;
      await decoded.decode();
      if (!state.previewActive || document.hidden) return;
      const img = document.getElementById("videoFeed");
      const previous = state.previewObjectUrl;
      if (!previewHealth.accept(sequence)) return;
      img.src = url;
      state.previewObjectUrl = url;
      if (previous) { try { URL.revokeObjectURL(previous); } catch {} }
    } finally {
      if (state.previewObjectUrl !== url) URL.revokeObjectURL(url);
    }
  } catch {
    // A failed request or JPEG decode never replaces the last successful frame.
    previewHealth.fail();
  } finally {
    clearTimeout(timeoutId);
    state.previewInFlight = false;
    renderPreviewHealth();
    schedulePreviewFrame(false, previewHealth.retryDelay(previewDelayMs()));
  }
}

function refreshVideoFeed() {
  state.previewActive = !document.hidden;
  previewHealth.setPaused(!state.previewActive);
  renderPreviewHealth();
  sendPreviewState(state.previewActive);
  schedulePreviewFrame(true);
}

function syncPreviewActivity() {
  const enabled = !document.hidden;
  if (!enabled && (Math.abs(state.manualThrottle) > 0.0001 || Math.abs(state.manualSteering) > 0.0001)) {
    // Best-effort STOP when the tab is hidden; server watchdog is authoritative.
    state.pointerControl.active = false;
    setManualTargets(0, 0, { immediateCurrent: true, sendNow: true });
  }
  state.previewActive = enabled;
  previewHealth.setPaused(!enabled);
  renderPreviewHealth();
  sendPreviewState(enabled);
  if (enabled) {
    schedulePreviewFrame(true);
    if (state.statusPollingReady) scheduleStatusPoll(0); // refresh immediately on return
  } else {
    stopPreviewLoop(false);
    if (state.statusPollingReady) scheduleStatusPoll(); // parked while hidden
  }
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
  } else if (!document.hidden && !state.estopEnabled
      && (pagePanels[state.page] || []).includes("manual")
      && (Math.abs(state.manualSteering) > 0.0001 || Math.abs(state.manualThrottle) > 0.0001)) {
    // Keep a held joystick/keyboard command alive; server expires it on lost connection.
    sendManualState(false);
  }
}

function updateManualPadSizing() {
  const area = document.getElementById("joystickArea");
  const layout = document.querySelector(".manual-layout-single");
  const side = document.querySelector(".manual-side-single");
  const shell = document.querySelector(".manual-shell");
  if (!area || !layout) return;
  area.style.width = "";
  area.style.height = "";
  // Stacked panels use intrinsic CSS square sizing; retain desktop fit-to-dock.
  if (window.matchMedia("(max-width: 1080px)").matches) return;
  const layoutRect = layout.getBoundingClientRect();
  const shellRect = shell ? shell.getBoundingClientRect() : layoutRect;
  const sideRect = side ? side.getBoundingClientRect() : { height: 0 };
  const layoutStyle = getComputedStyle(layout);
  const shellStyle = shell ? getComputedStyle(shell) : layoutStyle;
  const gap = parseFloat(layoutStyle.rowGap || layoutStyle.gap || "0") || 0;
  const shellPadY = (parseFloat(shellStyle.paddingTop || "0") || 0) + (parseFloat(shellStyle.paddingBottom || "0") || 0);
  const widthBudget = Math.max(176, Math.min(layoutRect.width, shellRect.width));
  const heightBudget = Math.max(176, Math.min(layoutRect.height, shellRect.height - shellPadY) - sideRect.height - gap);
  const size = Math.max(176, Math.floor(Math.min(widthBudget, heightBudget)));
  area.style.width = `${size}px`;
  area.style.height = `${size}px`;
}

function setupManualPadSizing() {
  const layout = document.querySelector(".manual-layout-single");
  const side = document.querySelector(".manual-side-single");
  const panel = document.querySelector('.dock-panel[data-panel="manual"]');
  if (!layout) return;
  if (state.manualPadObserver) {
    try { state.manualPadObserver.disconnect(); } catch {}
  }
  if (typeof ResizeObserver === "function") {
    state.manualPadObserver = new ResizeObserver(() => {
      window.requestAnimationFrame(updateManualPadSizing);
    });
    [layout, side, panel].filter(Boolean).forEach((el) => state.manualPadObserver.observe(el));
  }
  window.requestAnimationFrame(updateManualPadSizing);
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
    if (["input", "select", "textarea", "button"].includes(tag) || event.target?.isContentEditable) return;
    // R35: native disclosures, read-only diagnostics and other interactive
    // controls must not be interpreted as manual-drive key presses.
    if (event.target?.closest?.('summary, a[href], [data-drive-keys-ignore], [role="dialog"], [role="button"], [role="checkbox"], [role="switch"], [role="tab"]')) return;
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

  document.getElementById("previewLayoutBtn")?.addEventListener("click", previewWorkspaceLayout);
  document.getElementById("cancelLayoutPreviewBtn")?.addEventListener("click", cancelWorkspaceLayout);
  document.getElementById("essentialsOnly")?.addEventListener("change", (event) => {
    document.querySelector('#workspace .status-body')?.setAttribute("data-essentials-only", String(event.target.checked));
  });
  document.getElementById("saveLayoutBtn").addEventListener("click", () => {
    try {
      saveLayout(state.page, currentLayout());
      state.layoutPreview = null;
      updateLayoutPreviewControls();
      setBanner("statusBanner", `Saved ${state.page} layout.`, "muted");
    } catch {
      const message = document.getElementById("layoutPreviewMessage");
      if (message) message.textContent = "Could not save layout in this browser. Preview remains unsaved.";
    }
  });

  document.getElementById("resetLayoutBtn").addEventListener("click", () => {
    localStorage.removeItem(layoutStorageKey(state.page));
    applyLayout(state.page);
    setBanner("statusBanner", `Reset ${state.page} layout.`, "muted");
  });

  document.getElementById("openStyleSettingsBtn")?.addEventListener("click", () => {
    openStyleSettings();
  });

  document.getElementById("closeStyleSettingsBtn")?.addEventListener("click", () => {
    closeStyleSettings();
  });
  document.getElementById("styleSettingsModal")?.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const modal = document.getElementById("styleSettingsModal");
    if (!modal || modal.classList.contains("hidden")) return;
    const focusable = Array.from(modal.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), a[href], [tabindex="0"]'))
      .filter((el) => !el.closest("[inert]") && el.getClientRects().length);
    if (!focusable.length) return;
    if (event.shiftKey && document.activeElement === focusable[0]) {
      event.preventDefault();
      focusable[focusable.length - 1].focus();
    } else if (!event.shiftKey && document.activeElement === focusable[focusable.length - 1]) {
      event.preventDefault();
      focusable[0].focus();
    }
  });

  document.querySelectorAll("[data-close-style-modal]").forEach((el) => {
    el.addEventListener("click", () => closeStyleSettings());
  });

  document.getElementById("saveStyleSettingsBtn")?.addEventListener("click", () => {
    applyStyleOverridesToPage(collectStyleOverridesFromInputs());
    syncStyleInputsFromCurrentVars();
    closeStyleSettings();
    setBanner("statusBanner", "Saved web style settings for this browser.", "muted");
  });

  document.getElementById("resetStyleSettingsBtn")?.addEventListener("click", () => {
    resetStyleSettings();
    setBanner("statusBanner", "Reset web style settings to theme defaults.", "muted");
  });

  styleSettingsFields.forEach((field) => {
    const el = document.getElementById(field.id);
    if (!el) return;
    const handler = () => previewStyleOverridesFromInputs();
    el.addEventListener("input", handler);
    el.addEventListener("change", handler);
  });

  window.addEventListener("keydown", (event) => {
    const modal = document.getElementById("styleSettingsModal");
    if (event.key === "Escape" && !event.defaultPrevented && modal && !modal.classList.contains("hidden")) closeStyleSettings();
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

  document.getElementById("refreshSessionsBtn")?.addEventListener("click", refreshSessionsWithFeedback);

  document.getElementById("downloadSessionBtn")?.addEventListener("click", () => {
    downloadSelectedSession();
  });

  document.getElementById("deleteSessionBtn")?.addEventListener("click", async () => {
    try {
      await deleteSelectedSession();
    } catch (error) {
      setBanner("sessionExportMessage", error.message, "muted");
    }
  });

  document.getElementById("overlayToggleBtn").addEventListener("click", () => {
    const nextMode = (state.overlayMode + 1) % 3;
    setOverlayMode(nextMode);
    const message = nextMode === 0
      ? "Frame overlay off."
      : nextMode === 1
        ? "Overlay 1: throttle and steering enabled."
        : "Overlay 2: arc guide enabled.";
    setBanner("statusBanner", message, "muted");
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
      await refreshModels(true);
    } catch (error) {
      setBanner("modelMessage", `Cannot refresh models: ${error.message}. Retry after reconnecting.`, "muted");
    }
  });
  document.getElementById("loadModelBtn").addEventListener("click", async () => {
    try {
      await loadSelectedModel();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  });
  document.getElementById("deleteModelBtn")?.addEventListener("click", async () => {
    try {
      await deleteSelectedModel();
    } catch (error) {
      setBanner("modelMessage", error.message, "muted");
    }
  });

  document.getElementById("estopToggle").addEventListener("click", async () => {
    try {
      // A stale cached "active" value must never cause an unverified rearm.
      await setEstop(state.statusVerified ? !state.estopEnabled : true);
    } catch (error) {
      setBanner("statusBanner", error.message, "muted");
    }
  });

  document.getElementById("cameraResourceApply")?.addEventListener("click", applyPreviewResourceProfile);
  document.getElementById("cameraApplyBtn").addEventListener("click", async () => {
    try {
      await applyCameraConfig();
    } catch (error) {
      setBanner("cameraMessage", error.message, "muted");
    }
  });

  document.getElementById("cameraResolutionPreset").addEventListener("change", applyCameraResolutionPreset);
  document.getElementById('cameraRetryApply')?.addEventListener('click', applyCameraConfig);
  document.getElementById('motorRetryApply')?.addEventListener('click', applyMotorConfig);
  const cameraInputs = ['cameraResolutionPreset', 'cameraWidth', 'cameraHeight', 'cameraFps', 'cameraPreviewFps',
    'cameraPreviewQuality', 'cameraFormat', 'cameraStreamQuality', 'cameraAutoExposure', 'cameraAwb',
    'cameraExposureUs', 'cameraAnalogueGain', 'cameraExposureComp', 'cameraBrightness', 'cameraContrast',
    'cameraSaturation', 'cameraSharpness'];
  cameraInputs.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', () => settingsChanged('camera'));
    el.addEventListener('change', () => settingsChanged('camera'));
  });
  ['leftDirection', 'rightDirection', 'steeringDirection', 'leftMaxSpeed', 'rightMaxSpeed', 'leftBias', 'rightBias']
    .forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', () => settingsChanged('motor'));
      el.addEventListener('change', () => settingsChanged('motor'));
    });
  renderSettingsFeedback('camera');
  renderSettingsFeedback('motor');
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
  setupManualPadSizing();
  setupEvents();
  // A temporary outage in an optional initial GET must not abort startup
  // before the status polling loop and E-STOP safeguards are installed.
  for (const [read, banner] of [
    [refreshModels, "modelMessage"],
    [() => refreshSessions(false), "sessionExportMessage"],
    [loadCameraConfig, "cameraMessage"],
    [loadMotorConfig, "motorMessage"],
  ]) {
    try {
      await read();
    } catch (error) {
      setBanner(banner, `Cannot load data: ${error.message || "PiServer unreachable"}. Retry after reconnecting.`, "muted");
    }
  }
  syncPreviewActivity();
  document.addEventListener("visibilitychange", syncPreviewActivity);
  window.addEventListener("beforeunload", () => {
    sendPreviewState(false);
    stopPreviewLoop(false);
    if (state.stepTimer) clearInterval(state.stepTimer);
  });
  applyManualState();
  state.statusPollingReady = true;
  await pollStatus();
  state.previewHealthTimer = setInterval(renderPreviewHealth, 250);
}

window.addEventListener("load", init);
