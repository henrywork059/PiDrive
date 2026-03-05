# PATCH_NOTES_piCar_0_1_11

## Base

- Started from `piCar_0_1_10` (model already wired to camera frame; auto_steer/autopilot logic in place).

This patch:

1. Removes possible conflicts between the **drag pad** and **auto modes**.
2. Makes it much clearer when the Pi is missing the **TFLite runtime**, which would silently disable model control.

---

## 1. Frontend: disable drag-pad sends in auto modes

### File: `ui_script.py`

Previously, `sendControl()` would always POST steering/throttle to `/api/control`, regardless of mode:

```js
function sendControl() {
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
```

Now it explicitly **does nothing** when the current mode is **not manual**:

```js
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
```

Effect:

- **manual**:
  - Joystick works exactly as before; dragpad → `/api/control`.
- **auto_steer / autopilot**:
  - Joystick no longer spams manual steering/throttle to the backend.
  - Motors are driven only by `autopilot_step(...)` using the TFLite model outputs.

If you want to adjust throttle while in auto_steer, the simple workflow is:

1. Switch back to **manual**,
2. Set a new throttle with the drag pad,
3. Switch to **auto_steer** again (model will now steer using that new base throttle).

---

## 2. Backend: visible warning when TFLite runtime is missing

### File: `model_manager.py`

Previously, if **neither** `tflite_runtime` nor `tensorflow.lite` was installed:

- `InterpreterType` became `None`,
- But there was no clear message on the Pi console,
- `/api/model/load` could still “succeed” (storing only the model name),
- `autopilot_step(...)` then had no interpreter and quietly did nothing.

Now the interpreter import block is:

```python
# Try to import a TFLite Interpreter implementation
InterpreterType = None
try:
    from tflite_runtime.interpreter import Interpreter as _Interpreter  # type: ignore
    InterpreterType = _Interpreter
except Exception:
    try:
        from tensorflow.lite.python.interpreter import Interpreter as _Interpreter  # type: ignore
        InterpreterType = _Interpreter
    except Exception:
        InterpreterType = None
        # This will be printed on the Pi console so the user understands
        # why auto_steer/autopilot are not moving the car.
        print("[WARN] No TFLite interpreter backend found. Install 'tflite-runtime' or TensorFlow Lite on the Pi to enable auto_steer/autopilot.")  # NO_TFLITE_BACKEND
```

So if you start `server.py` in a terminal and see this warning:

> `[WARN] No TFLite interpreter backend found. Install 'tflite-runtime' or TensorFlow Lite on the Pi to enable auto_steer/autopilot.`

then you know:

- The UI will still let you upload/select a model,
- But **the car will never drive itself** until you install a TFLite runtime.

Recording logic and manual mode behaviour remain unchanged.

