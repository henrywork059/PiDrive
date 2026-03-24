const state = {
  activePage: "manual",
  timer: null,
};

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.message || `Request failed: ${response.status}`);
  }
  return data;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function setBanner(message) {
  const element = document.getElementById("statusBanner");
  if (element) element.textContent = message;
}

function renderStatus(payload) {
  const data = payload || {};
  state.activePage = String(data.active_page || state.activePage || "manual");
  document.body.setAttribute("data-page", state.activePage);
  document.querySelectorAll(".tab-btn[data-page]").forEach((button) => {
    const active = button.dataset.page === state.activePage;
    button.classList.toggle("active", active);
  });
  setText("metricDriveState", data.gui_ready ? "ready" : "loading");
  setText("metricApplied", "placeholder");
  setText("metricManual", state.activePage);
  setText("metricLastSave", "local style only");
  setText("metricPreview", data.preview || "placeholder");
  setText("metricCamera", "not wired");
  setText("metricModel", "empty");
  setText("metricAlgorithm", "gui-shell");
  setText("metricMaxThrottle", "--");
  setText("metricSteerMix", "--");
  setText("metricSteerBias", "--");
  setText("metricWheels", "-- / --");
  setText("metricFps", "0.0 FPS");
  setText("metricBackend", data.runtime_mode || "gui-shell");
  setText("metricError", "none");
  setText("shellUptime", `${Number(data.uptime_s || 0).toFixed(1)} s`);
  setText("shellPage", state.activePage);
  setBanner(data.banner || "GUI shell ready.");

  const list = document.getElementById("shellNotes");
  if (list) {
    list.innerHTML = "";
    (Array.isArray(data.notes) ? data.notes : []).forEach((note) => {
      const item = document.createElement("li");
      item.textContent = String(note);
      list.appendChild(item);
    });
  }
}

async function refresh() {
  const data = await fetchJSON("/api/status");
  renderStatus(data);
}

async function selectPage(page) {
  const data = await fetchJSON("/api/page", {
    method: "POST",
    body: JSON.stringify({ page }),
  });
  renderStatus(data.status || {});
}

window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab-btn[data-page]").forEach((button) => {
    button.addEventListener("click", () => selectPage(button.dataset.page || "manual"));
  });
  document.getElementById("openStyleSettingsBtn")?.addEventListener("click", () => {
    window.location.href = "/settings";
  });
  document.getElementById("saveLayoutBtn")?.addEventListener("click", () => {
    setBanner("Layout persistence is not wired yet. This is the empty GUI base.");
  });
  document.getElementById("resetLayoutBtn")?.addEventListener("click", () => {
    setBanner("Layout reset is not wired yet. Use this shell as the new GUI control base.");
  });

  refresh();
  state.timer = window.setInterval(refresh, 1000);
});
