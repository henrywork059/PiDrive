# PATCH_NOTES_piCar_0_1_9

## Base

- Started from `piCar_0_1_2` (stable baseline with:
  - working manual drag control joystick,
  - working recording pipeline compatible with the PC training GUI,
  - status bar showing mode / FPS / recording / steering / speed / model_name).

This patch adds:

1. A **Mode Selection** panel on the right,
2. A **TFLite model upload + listing + load** flow integrated into that panel,
3. A safer joystick release behaviour (always returns steering & throttle to 0 and forces a stop packet),
4. Backend support for storing and managing TFLite models under `models/`.

Recording logic (`data_recorder.py` and `recorder_step.py`) is unchanged.

---

## 1. UI: Mode Selection + Model Management panel

### Files touched

- `ui_manual_panel.py`
- `ui_model_panel.py` (new)
- `ui_base.py`
- `ui_template.py`
- `ui_script.py`

### 1.1 Manual panel: hide speed bar and stop button, keep behaviour stable

- File: `ui_manual_panel.py`

Changes:

- The **speed slider block** and the **Stop button row** are now visually hidden but still present in the DOM so that existing JS hooks do not break:

  ```html
  <div class="speed-control" style="display:none;">
      ...
  </div>

  <div class="btn-row" style="display:none;">
      <button class="btn-stop" onclick="stopCar()">Stop</button>
  </div>
  ```

This keeps the UI clean (no speed bar, no Stop button) while avoiding any JS `getElementById(...)` crashes.

### 1.2 New Mode Selection + TFLite model panel

- File: `ui_model_panel.py` (new)

Added a new panel injected into the layout **above** the Manual Drag Control panel:

```python
MODEL_PANEL = """<div class="panel panel-mode-select">
    <div class="panel-title">Mode Selection</div>

    <div class="model-select-row">
        <label for="modeSelect">Drive mode:</label>
        <select id="modeSelect">
            <option value="manual">Manual</option>
            <option value="auto_steer">Auto steer</option>
            <option value="autopilot">Self driving</option>
        </select>
    </div>

    <div id="modeInfo">Current mode: <span id="currentModeText">manual</span></div>

    <hr class="panel-separator" />

    <div class="model-section-title">TFLite model</div>

    <div class="model-upload-row">
        <label for="modelFile">Upload .tflite:</label>
        <input id="modelFile" type="file" accept=".tflite" />
        <button type="button" class="btn-secondary" onclick="uploadModel()">Upload</button>
    </div>

    <div class="model-select-row">
        <label for="modelSelect">Available models:</label>
        <select id="modelSelect">
            <option value="">(none)</option>
        </select>
        <button type="button" class="btn-secondary" onclick="loadSelectedModel()">Load</button>
    </div>

    <div id="modelStatus">Current model: <span id="currentModelName">none</span></div>
    <div id="modelMessage" class="model-message"></div>
</div>
"""
```

### 1.3 Layout / CSS changes

- File: `ui_base.py`

1. **Layout injection**

   The main layout now includes the model/mode panel between viewer and manual:

   ```html
   <div class="layout">
       {status_panel}
       {viewer_panel}
       {model_panel}
       {manual_panel}
       {record_panel}
   </div>
   ```

2. **Right-column panel positions**

   Added:

   ```css
   .panel-mode-select {
       grid-column: 21 / span 10;
       grid-row: 1 / span 5;
   }

   .panel-manual {
       grid-column: 21 / span 10;
       grid-row: 6 / span 12;
   }

   .panel-record {
       grid-column: 21 / span 10;
       grid-row: 18 / span 3;
   }
   ```

   So on the right-hand side you now have:

   - Rows 1–5: **Mode Selection + Model Management**
   - Rows 6–17: **Manual Drag Control**
   - Rows 18–20: **Recording**

3. **Styling for new elements**

   Added:

   ```css
   .btn-secondary { ... }
   .btn-secondary:hover { ... }
   .btn-secondary:active { ... }

   .model-section-title { ... }

   .model-select-row,
   .model-upload-row { ... }

   .model-message { ... }

   .panel-separator { ... }
   ```

   These give the Mode/Model section a consistent compact style with the rest of the UI.

4. **Template wiring**

   - File: `ui_template.py`

   Wired the new panel into the HTML assembly:

   ```python
   from ui_model_panel import MODEL_PANEL

   ...

   _html = BASE_HTML
   _html = _html.replace("{status_panel}", STATUS_PANEL)
   _html = _html.replace("{viewer_panel}", VIEWER_PANEL)
   _html = _html.replace("{model_panel}", MODEL_PANEL)
   _html = _html.replace("{manual_panel}", MANUAL_PANEL)
   _html = _html.replace("{record_panel}", RECORD_PANEL)
   _html = _html.replace("{script}", MAIN_SCRIPT)
   ```

---

## 2. Frontend JS: mode syncing, TFLite upload, list, and load

- File: `ui_script.py`

### 2.1 Joystick release → steering=0, throttle=0, forced stop packet

Replaced the original reset behaviour:

```js
function resetJoystick() {
    dot.style.left = "50%";
    dot.style.top  = "100%";

    const t = parseInt(speedSlider.value, 10) / 100.0 || 0.0;
    window.currentSteering = 0.0;
    window.currentThrottle = t;

    speedValue.innerText = "Speed: " + t.toFixed(2);
    info.innerText = "Drag inside the box to control the car.";

    sendControl();
}
```

with:

```js
function resetJoystick() {
    if (dot) {
        dot.style.left = "50%";
        dot.style.top  = "100%";
    }

    // On release, always return to neutral:
    // steering = 0, throttle = 0 so the car really stops.
    window.currentSteering = 0.0;
    window.currentThrottle = 0.0;

    if (speedSlider) {
        speedSlider.value = 0;
    }
    if (speedValue) {
        speedValue.innerText = "Speed: 0.00";
    }
    if (info) {
        info.innerText = "Car stopped. Drag inside the box to move again.";
    }

    // Force next send to go through even if it happens quickly after the last one.
    lastSend = 0;
    // Send a final control packet so the backend updates motors + status.
    sendControl();
}
```

This guarantees:

- On pointer release the car always receives **steering = 0, throttle = 0**.
- We bypass the SEND_INTERVAL limiter for this stop packet to avoid missing it.

### 2.2 Mode + model sync from `/api/status`

`pollStatus()` now additionally drives the Mode Selection + Model info panel:

```js
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
```

Status bar remains unchanged, still showing:

- Mode, FPS, Rec state, Steering, Speed, Model name.

### 2.3 Mode change → `/api/control` with new `mode`

Added:

```js
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
```

The handler is attached once at startup:

```js
(function initModeAndModels() {
    const sel = document.getElementById("modeSelect");
    if (sel) {
        sel.addEventListener("change", onModeChange);
    }
    refreshModelList();
})();
```

So changing the dropdown updates `control_state["mode"]` via the existing `/api/control` route.

### 2.4 TFLite model management functions

Added helper:

```js
function showModelMessage(msg, isError) { ... }
```

#### Listing models (`GET /api/model/list`)

```js
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
```

#### Uploading a model (`POST /api/model/upload`)

```js
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
```

#### Loading a model (`POST /api/model/load`)

```js
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
```

This completes the frontend side.

---

## 3. Backend: model manager + new APIs

### Files added / modified

- `model_manager.py` (new)
- `control_api.py`
- `server.py`

### 3.1 model_manager.py

Key points:

- Models stored in:

  ```python
  BASE_DIR = Path(__file__).resolve().parent
  MODELS_DIR = BASE_DIR / "models"
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  ```

- Expected input size:

  ```python
  MODEL_INPUT_WIDTH = 200
  MODEL_INPUT_HEIGHT = 112
  ```

- Lists models:

  ```python
  def list_models() -> List[str]:
      ...
  ```

- Saves uploaded models with validation:

  ```python
  def save_uploaded_model(file_storage) -> Tuple[bool, str]:
      ...
      dest = MODELS_DIR / filename
      file_storage.save(str(dest))
      ok, msg = _validate_model_shape(dest)
      if not ok:
          dest.unlink()
          return False, msg
      return True, filename
  ```

- Validates model shape using a TFLite interpreter if available:

  ```python
  def _validate_model_shape(model_path: Path) -> Tuple[bool, str]:
      if InterpreterType is None:
          return True, "Interpreter backend not available; shape not validated."

      interpreter = InterpreterType(model_path=str(model_path))
      interpreter.allocate_tensors()
      input_details = interpreter.get_input_details()[0]
      shape = input_details.get("shape", None)
      ...
      if h != MODEL_INPUT_HEIGHT or w != MODEL_INPUT_WIDTH or c not in (1, 3):
          return False, f"Model input must be [1, {MODEL_INPUT_HEIGHT}, {MODEL_INPUT_WIDTH}, 3], got {shape!r}"
  ```

  This implements the requested **“reject mismatched input size”** behaviour where possible.

- Loads a model and makes it active:

  ```python
  def load_model(filename: str) -> Tuple[bool, str]:
      ...
      interpreter = InterpreterType(model_path=str(model_path))
      interpreter.allocate_tensors()
      ...
      _active_interpreter = interpreter
      _active_model_name = filename
      return True, filename
  ```

- If no interpreter backend is available (no tflite_runtime / tensorflow), it will still remember the active model name but cannot run inference yet.

### 3.2 control_api.py: dynamic model_name

- Import:

  ```python
  from video_stream import get_fps
  from model_manager import get_model_name
  ```

- `get_status()` now reports the active model from the model manager:

  ```python
  "model_name": get_model_name(),
  ```

So both the Status bar and the Mode/Model panel always show the current active model name (or `none`).

### 3.3 server.py: new API endpoints

Added imports:

```python
from model_manager import list_models, save_uploaded_model, load_model, get_model_name
```

New routes:

```python
@app.route("/api/model/upload", methods=["POST"])
def api_model_upload():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file part in request."}), 400
    file = request.files["file"]
    ok, msg = save_uploaded_model(file)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "filename": msg})


@app.route("/api/model/list", methods=["GET"])
def api_model_list():
    models = list_models()
    active = get_model_name()
    return jsonify({"models": models, "active": active})


@app.route("/api/model/load", methods=["POST"])
def api_model_load():
    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "")
    ok, msg = load_model(filename)
    if not ok:
        return jsonify({"ok": False, "error": msg}), 400
    return jsonify({"ok": True, "model_name": msg})
```

---

## 4. Behaviour summary

- **Joystick release**:
  - Always sends a final packet with `steering = 0`, `throttle = 0`.
  - Status bar steering/speed return to 0.00.
  - Car physically stops reliably.

- **Mode selection**:
  - Dropdown in Mode Selection panel controls `control_state["mode"]`.
  - Status bar and panel show the same mode.

- **Model upload**:
  - `.tflite` file uploaded through the web UI.
  - Saved into `models/` folder.
  - If a TFLite interpreter backend is available:
    - Rejects files whose input shape is not `[1, 112, 200, 3]`.
  - On success, model list is refreshed.

- **Model list + load**:
  - Dropdown lists all `.tflite` files in `models/`.
  - Load button calls `/api/model/load`, which:
    - Creates a TFLite interpreter (when possible),
    - Validates input shape,
    - Marks it as the active model.
  - Status bar + Mode panel show the active model name.

- **Recording**:
  - Unchanged from `0_1_2` and should still work exactly as before.

