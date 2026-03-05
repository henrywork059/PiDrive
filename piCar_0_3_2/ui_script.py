# ui_script.py

MAIN_SCRIPT = """
window.currentSteering = 0.0;
window.currentThrottle = 0.0;

let lastSend = 0;
const SEND_INTERVAL_MS = 80;

function sendControl() {
    // In non-manual modes, control is driven by the model; ignore drag-pad sends
    const modeSelect = document.getElementById("modeSelect");
    if (modeSelect && modeSelect.value !== "manual") {
        return;
    }

    const now = Date.now();
    if (now - lastSend < SEND_INTERVAL_MS) return;
    lastSend = now;

    fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            steering: window.currentSteering,
            throttle: window.currentThrottle
        })
    }).catch(console.error);
}

function pollStatus() {
    fetch("/api/status")
        .then(r => r.json())
        .then(data => {
            // Robust field handling across versions
            const thr = (typeof data.throttle === "number") ? data.throttle : ((typeof data.speed === "number") ? data.speed : 0.0);

            const recDotHtml = '<span class="rec-dot ' + (data.recording ? 'rec-dot-on' : 'rec-dot-off') + '"></span>';
            const txt =
                "Mode: " + data.mode +
                " | FPS: " + data.fps.toFixed(1) +
                " | Rec: " + recDotHtml +
                " | Steering: " + data.steering.toFixed(2) +
                " | Throttle: " + thr.toFixed(2) +
                " | Model: " + data.model_name;
            const statusEl = document.getElementById("statusBarMain");
            if (statusEl) {
                statusEl.innerHTML = txt;
            }

            // Update Mode Selection panel
            const modeSpan = document.getElementById("currentModeText");
            if (modeSpan) {
                modeSpan.textContent = data.mode;
            }
            const modeSelect = document.getElementById("modeSelect");
            if (modeSelect) {
                for (let i = 0; i < modeSelect.options.length; i++) {
                    if (modeSelect.options[i].value === data.mode) {
                        modeSelect.value = data.mode;
                        break;
                    }
                }
            }

            // Update model info panel
            const modelNameSpan = document.getElementById("currentModelName");
            if (modelNameSpan) {
                modelNameSpan.textContent = data.model_name || "none";
            }


            const btn = document.getElementById("recordToggleBtn");
            const txtNode = document.getElementById("recordStatusText");
            if (btn && txtNode) {
                if (data.recording) {
                    btn.classList.remove("btn-record-off");
                    btn.classList.add("btn-record-on");
                    txtNode.innerHTML = '<span class="rec-dot rec-dot-on"></span> Recording';
                } else {
                    btn.classList.remove("btn-record-on");
                    btn.classList.add("btn-record-off");
                    txtNode.innerHTML = '<span class="rec-dot rec-dot-off"></span> Recording';
                }
            }

            // If recording just stopped, refresh the session list so the new folder appears.
            if (typeof window._lastRecordingState === "boolean") {
                if (window._lastRecordingState === true && data.recording === false) {
                    refreshRecordingList();
                }
            }
            window._lastRecordingState = !!data.recording;
        })
        .catch(console.error);
}

setInterval(pollStatus, 500);

function onModeChange() {
    const sel = document.getElementById("modeSelect");
    if (!sel) return;
    const newMode = sel.value || "manual";

    const steering = window.currentSteering || 0.0;
    const throttle = window.currentThrottle || 0.0;

    // Force immediate send of mode change regardless of SEND_INTERVAL_MS
    lastSend = 0;
    fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            steering: steering,
            throttle: throttle,
            mode: newMode
        })
    }).catch(console.error);
}

function showModelMessage(msg, isError) {
    const el = document.getElementById("modelMessage");
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = isError ? "#ff8080" : "#9fa8c6";
}

function refreshModelList() {
    const select = document.getElementById("modelSelect");
    if (!select) return;

    fetch("/api/model/list")
        .then(r => r.json())
        .then(data => {
            const models = data.models || [];
            const active = data.active || "";

            select.innerHTML = "";
            if (!models.length) {
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "(none)";
                select.appendChild(opt);
            } else {
                models.forEach(name => {
                    const opt = document.createElement("option");
                    opt.value = name;
                    opt.textContent = name;
                    select.appendChild(opt);
                });
            }

            if (active) {
                select.value = active;
                const modelNameSpan = document.getElementById("currentModelName");
                if (modelNameSpan) {
                    modelNameSpan.textContent = active;
                }
            }

            showModelMessage("", false);
        })
        .catch(err => {
            console.error(err);
            showModelMessage("Failed to list models.", true);
        });
}

function uploadModel() {
    const fileInput = document.getElementById("modelFile");
    if (!fileInput || !fileInput.files || !fileInput.files.length) {
        showModelMessage("Please choose a .tflite file first.", true);
        return;
    }
    const file = fileInput.files[0];
    if (!file.name.toLowerCase().endsWith(".tflite")) {
        showModelMessage("Only .tflite files are supported.", true);
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    showModelMessage("Uploading model...", false);

    fetch("/api/model/upload", {
        method: "POST",
        body: formData
    })
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                showModelMessage(data.error || "Upload failed.", true);
                return;
            }
            showModelMessage("Model uploaded successfully.", false);
            // Refresh model dropdown to include the new file
            refreshModelList();
        })
        .catch(err => {
            console.error(err);
            showModelMessage("Upload failed.", true);
        });
}

function loadSelectedModel() {
    const select = document.getElementById("modelSelect");
    if (!select || !select.value) {
        showModelMessage("Please select a model to load.", true);
        return;
    }
    const filename = select.value;
    showModelMessage("Loading model: " + filename + "...", false);

    fetch("/api/model/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename })
    })
        .then(r => r.json())
        .then(data => {
            if (!data.ok) {
                showModelMessage(data.error || "Failed to load model.", true);
                return;
            }
            const active = data.model_name || filename;
            const modelNameSpan = document.getElementById("currentModelName");
            if (modelNameSpan) {
                modelNameSpan.textContent = active;
            }
            showModelMessage("Model loaded: " + active, false);
        })
        .catch(err => {
            console.error(err);
            showModelMessage("Failed to load model.", true);
        });
}

// Attach mode change handler and initial model list refresh once DOM is ready enough
(function initModeAndModels() {
    const sel = document.getElementById("modeSelect");
    if (sel) {
        sel.addEventListener("change", onModeChange);
    }
    refreshModelList();

    // Load available recordings for download (and keep it refreshed when recording stops)
    refreshRecordingList();
})();


function refreshRecordingList() {
    const select = document.getElementById("recordSessionSelect");
    if (!select) return;

    fetch("/api/record/list")
        .then(r => r.json())
        .then(data => {
            const sessions = data.sessions || [];
            const current = select.value;

            select.innerHTML = "";
            if (!sessions.length) {
                const opt = document.createElement("option");
                opt.value = "";
                opt.textContent = "(no recordings yet)";
                select.appendChild(opt);
                return;
            }

            sessions.forEach(name => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.textContent = name;
                select.appendChild(opt);
            });

            // Keep selection if possible, otherwise default to newest
            if (current && sessions.includes(current)) {
                select.value = current;
            } else {
                select.value = sessions[0];
            }
        })
        .catch(console.error);
}


function downloadSelectedRecording() {
    const select = document.getElementById("recordSessionSelect");
    if (!select) return;
    const session = (select.value || "").trim();
    if (!session || session.startsWith("(")) {
        alert("No recording session available to download yet.");
        return;
    }
    // Use a direct navigation so the browser downloads the zip file.
    window.location = "/api/record/download?session=" + encodeURIComponent(session);
}


function deleteSelectedRecording() {
    const select = document.getElementById("recordSessionSelect");
    if (!select) return;
    const session = (select.value || "").trim();
    if (!session || session.startsWith("(")) {
        alert("No recording session available to delete yet.");
        return;
    }

    if (!confirm("Delete recording session '" + session + "'? This cannot be undone.")) {
        return;
    }

    fetch("/api/record/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session: session })
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) {
            alert(data.error || "Failed to delete session.");
            return;
        }
        refreshRecordingList();
    })
    .catch(err => {
        console.error(err);
        alert("Failed to delete session.");
    });
}



function stopCar() {
    window.currentSteering = 0.0;
    window.currentThrottle = 0.0;

    const dot = document.getElementById("joystickDot");
    const info = document.getElementById("joystickInfo");

    if (dot) {
        dot.style.left = "50%";
        dot.style.top  = "100%";
    }
    if (info) {
        info.innerText = "Car stopped. Drag inside the box to move again.";
    }

    fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            steering: 0.0,
            throttle: 0.0,
            mode: "manual"
        })
    }).catch(console.error);
}

function toggleRecord() {
    fetch("/api/record/toggle", {
        method: "POST"
    })
    .then(r => r.json())
    .then(data => {
        const recording = !!data.recording;
        const btn = document.getElementById("recordToggleBtn");
        const txtNode = document.getElementById("recordStatusText");
        if (btn && txtNode) {
            if (recording) {
                btn.classList.remove("btn-record-off");
                btn.classList.add("btn-record-on");
                txtNode.innerHTML = '<span class="rec-dot rec-dot-on"></span> Recording';
            } else {
                btn.classList.remove("btn-record-on");
                btn.classList.add("btn-record-off");
                txtNode.innerHTML = '<span class="rec-dot rec-dot-off"></span> Recording';
            }
        }
    })
    .catch(console.error);
}


(function setupJoystick() {
    const area = document.getElementById("joystickArea");
    const dot = document.getElementById("joystickDot");
    const info = document.getElementById("joystickInfo");

    let active = false;


function updateFromPoint(x, y) {
    const r = area.getBoundingClientRect();

    // Normalize pointer position to [0, 1] within the full square area
    let relX = (x - r.left) / r.width;
    let relY = (y - r.top) / r.height;

    // Clamp to [0, 1]
    relX = Math.max(0, Math.min(1, relX));
    relY = Math.max(0, Math.min(1, relY));

    // Map to steering (-1 .. 1) and throttle (0 .. 1)
    const steering = (relX - 0.5) * 2.0;  // left=-1, center=0, right=+1
    const throttle = 1.0 - relY;          // bottom=0, top=1

    // Move joystick dot within the square
    const dotX = relX * 100.0;
    const dotY = relY * 100.0;
    dot.style.left = dotX + "%";
    dot.style.top  = dotY + "%";

    window.currentSteering = steering;
    window.currentThrottle = throttle;

    info.innerText =
        "Joystick steering=" + steering.toFixed(2) +
        " throttle=" + throttle.toFixed(2);

    sendControl();
}

    function resetJoystick() {
        if (dot) {
            dot.style.left = "50%";
            dot.style.top  = "100%";
        }

        // On release, always return to neutral:
        // steering = 0, throttle = 0 so the car really stops.
        window.currentSteering = 0.0;
        window.currentThrottle = 0.0;

        if (info) {
            info.innerText = "Car stopped. Drag inside the box to move again.";
        }

        // Force next send to go through even if it happens quickly after the last one.
        lastSend = 0;
        // Send a final control packet so the backend updates motors + status.
        sendControl();
    }

    area.addEventListener("mousedown", (e) => {
        active = true;
        updateFromPoint(e.clientX, e.clientY);
    });

    window.addEventListener("mousemove", (e) => {
        if (!active) return;
        updateFromPoint(e.clientX, e.clientY);
    });

    window.addEventListener("mouseup", () => {
        if (!active) return;
        active = false;
        resetJoystick();
    });

    area.addEventListener("touchstart", (e) => {
        e.preventDefault();
        active = true;
        const t = e.touches[0];
        updateFromPoint(t.clientX, t.clientY);
    }, { passive: false });

    area.addEventListener("touchmove", (e) => {
        e.preventDefault();
        if (!active) return;
        const t = e.touches[0];
        updateFromPoint(t.clientX, t.clientY);
    }, { passive: false });

    area.addEventListener("touchend", (e) => {
        e.preventDefault();
        if (!active) return;
        active = false;
        resetJoystick();
    }, { passive: false });

    resetJoystick();
})();
"""
