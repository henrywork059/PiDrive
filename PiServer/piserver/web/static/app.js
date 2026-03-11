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
    system: { c: 9, r: 13, w: 16, h: 2 }
  },
  training: {
    status: { c: 1, r: 1, w: 8, h: 2 },
    viewer: { c: 1, r: 3, w: 14, h: 9 },
    drive: { c: 15, r: 1, w: 10, h: 6 },
    manual: { c: 15, r: 7, w: 10, h: 5 },
    record: { c: 1, r: 12, w: 8, h: 3 },
    system: { c: 9, r: 12, w: 16, h: 3 }
  },
  auto: {
    status: { c: 1, r: 1, w: 7, h: 2 },
    viewer: { c: 1, r: 3, w: 16, h: 10 },
    drive: { c: 17, r: 1, w: 8, h: 6 },
    manual: { c: 17, r: 7, w: 8, h: 4 },
    record: { c: 1, r: 13, w: 7, h: 2 },
    system: { c: 8, r: 13, w: 17, h: 2 }
  }
};

const state = {
  page: "manual",
  manualSteering: 0,
  manualThrottle: 0,
  maxThrottle: 0.55,
  steerMix: 0.50,
  dragging: null,
  resizing: null,
  latestStatus: null
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

function loadLayout(page) {
  try {
    const raw = localStorage.getItem(layoutStorageKey(page));
    if (!raw) return structuredClone(defaultLayouts[page]);
    const parsed = JSON.parse(raw);
    return Object.assign(structuredClone(defaultLayouts[page]), parsed);
  } catch {
    return structuredClone(defaultLayouts[page]);
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
    out[panel.dataset.panel] = {
      c: Number(panel.style.getPropertyValue("--c") || panel.style.getPropertyValue("c") || panel.dataset.c || 1),
      r: Number(panel.style.getPropertyValue("--r") || panel.dataset.r || 1),
      w: Number(panel.style.getPropertyValue("--w") || panel.dataset.w || 6),
      h: Number(panel.style.getPropertyValue("--h") || panel.dataset.h || 3)
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
      if (event.target.closest("button, select, input")) return;
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
      const box = readPanelBox(panel);
      panel.classList.add("resizing");
      state.resizing = {
        panel,
        startX: event.clientX,
        startY: event.clientY,
        box
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

function setActivePage(page) {
  state.page = page;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.page === page);
  });
  applyLayout(page);
  sendControlUpdate({ current_page: page });
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
  document.getElementById("metricAlgorithm").textContent = data.active_algorithm;
  document.getElementById("metricModel").textContent = data.active_model || "none";
  document.getElementById("metricFps").textContent = Number(data.fps || 0).toFixed(1);
  document.getElementById("metricRec").textContent = data.recording ? "on" : "off";
  document.getElementById("metricWheels").textContent = `${Number(data.motor_left).toFixed(2)} / ${Number(data.motor_right).toFixed(2)}`;
  document.getElementById("metricCamera").textContent = `${data.camera_backend} ${data.camera_width}×${data.camera_height}`;
  setBanner("statusBanner", data.system_message || "Ready.", "muted");

  const badge = document.getElementById("recordStateBadge");
  badge.textContent = data.recording ? "on" : "off";
  badge.classList.toggle("on", !!data.recording);
  badge.classList.toggle("off", !data.recording);

  if (data.git) {
    const gitText = data.git.ok
      ? `${data.git.branch} · ${data.git.commit}${data.git.dirty ? " · modified" : ""}`
      : (data.git.message || "No Git repo");
    document.getElementById("gitStatusText").textContent = gitText;
  }
}

async function pollStatus() {
  try {
    const data = await fetchJson("/api/status");
    updateStatusUi(data);
  } catch (error) {
    setBanner("systemMessage", error.message, "muted");
  }
}

async function refreshAlgorithms() {
  const data = await fetchJson("/api/algorithms");
  const select = document.getElementById("algorithmSelect");
  select.innerHTML = "";
  data.algorithms.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.name;
    opt.textContent = `${item.label} (${item.name})`;
    select.appendChild(opt);
  });
  select.value = state.latestStatus?.active_algorithm || "manual";
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
    body: JSON.stringify({ filename: select.value })
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
    body: JSON.stringify({ enabled })
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
    btn.addEventListener("click", () => setActivePage(btn.dataset.page));
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
    } catch (error) {
      setBanner("systemMessage", error.message, "muted");
    }
  });

  document.getElementById("gitPullBtn").addEventListener("click", () => runSystemAction("/api/system/update", "systemMessage"));
  document.getElementById("restartBtn").addEventListener("click", () => runSystemAction("/api/system/restart", "systemMessage"));
  document.getElementById("estopBtn").addEventListener("click", () => setEstop(true));
  document.getElementById("clearEstopBtn").addEventListener("click", () => setEstop(false));
}

function syncControlsFromStatus(data) {
  state.maxThrottle = Number(data.max_throttle || 0.55);
  state.steerMix = Number(data.steer_mix || 0.5);
  document.getElementById("maxThrottle").value = Math.round(state.maxThrottle * 100);
  document.getElementById("manualSpeed").value = Math.round(state.maxThrottle * 100);
  document.getElementById("steerMix").value = Math.round(state.steerMix * 100);
  document.getElementById("algorithmSelect").value = data.active_algorithm || "manual";
  updateRangeText();
  if (data.current_page) {
    setActivePage(data.current_page);
  }
}

async function init() {
  applyLayout(state.page);
  updateRangeText();
  setupDocking();
  setupJoystick();
  setupEvents();
  await refreshAlgorithms();
  await refreshModels();
  const status = await fetchJson("/api/status");
  updateStatusUi(status);
  syncControlsFromStatus(status);
  setInterval(pollStatus, 700);
}

window.addEventListener("load", init);
