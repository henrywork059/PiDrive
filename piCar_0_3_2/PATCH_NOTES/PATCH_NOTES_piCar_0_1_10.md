# PATCH_NOTES_piCar_0_1_10

## Base

- Started from `piCar_0_1_9` (which itself was based on `piCar_0_1_2`), where:
  - Manual joystick control + recording were working,
  - Mode Selection panel + TFLite model upload/list/load were already in place,
  - Model manager could load a TFLite model and expose the active interpreter/name,
  - But the model output was **not yet used** to drive the car.

This patch **wires the loaded TFLite model into the runtime**, so that:

- In **auto_steer** mode: the model controls **steering only**, throttle remains user-controlled.
- In **autopilot** mode: the model controls **both steering and throttle**.
- Recording continues to log what actually gets sent to the motors.

---

## 1. Camera: expose latest raw frame for inference

### File: `camera.py`

Added:

```python
    def get_latest_frame(self):
        """Return latest raw BGR frame (np.ndarray) or None."""
        with self._frame_lock:
            frame = None if self._frame is None else self._frame.copy()
        return frame
```

This is a small, safe addition that:

- Reuses the same `_frame` the MJPEG stream already uses,
- Returns a copy (so inference code cannot mutate the capture buffer),
- Does **not** change existing `get_jpeg_frame()` behaviour.

---

## 2. New module: `autopilot.py` (TFLite inference on frames)

### File: `autopilot.py` (new)

Purpose: keep **all inference logic** in one place, away from `control_api` and `model_manager`.

Key parts:

- Imports:

  ```python
  import numpy as np
  import cv2
  from model_manager import get_interpreter, MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT
  ```

  Both `numpy` and `cv2` are optional; if not available, autopilot simply does nothing.

- Preprocessing:

  ```python
  def _prepare_input(frame_bgr) -> Optional[np.ndarray]:
      # BGR -> RGB
      img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
      img = cv2.resize(img, (MODEL_INPUT_WIDTH, MODEL_INPUT_HEIGHT))
      img = img.astype("float32") / 255.0
      img = np.expand_dims(img, axis=0)  # [1, H, W, 3]
      return img
  ```

- Handling quantized vs float inputs:

  ```python
  def _quantize_if_needed(x, input_details):
      dtype = input_details.get("dtype")
      if dtype == np.float32:
          return x.astype(np.float32)

      scale, zp = input_details.get("quantization", (0.0, 0))
      ...
      # handle int8/uint8 by applying (x / scale + zp) and clipping
  ```

- Handling quantized outputs:

  ```python
  def _dequantize_output(y, output_details):
      dtype = output_details.get("dtype")
      if dtype is None or dtype == np.float32:
          return y.astype("float32")
      scale, zp = output_details.get("quantization", (0.0, 0))
      y = y.astype("float32")
      if scale and scale > 0.0:
          y = scale * (y - float(zp))
      return y
  ```

- Main entry point:

  ```python
  def predict_uv_from_camera(camera) -> Optional[Tuple[float, float]]:
      interpreter = get_interpreter()
      ...
      frame = camera.get_latest_frame()
      ...
      x = _prepare_input(frame)
      x = _quantize_if_needed(x, input_details)
      interpreter.set_tensor(input_details["index"], x)
      interpreter.invoke()
      output_details = interpreter.get_output_details()[0]
      y = interpreter.get_tensor(output_details["index"])
      y = _dequantize_output(y, output_details)

      y = y.reshape(-1)
      if y.size < 2:
          return None

      u = float(y[0])   # steering
      v = float(y[1])   # throttle

      # Safety clipping
      u = max(-1.0, min(1.0, u))
      v = max(0.0, min(1.0, v))

      return u, v
  ```

Semantics:

- Uses the **same image size and normalization** as the training GUI:
  - 200×112, RGB, normalized to [0, 1].
- Treats outputs as:
  - `u` = steering (mapped from dataset’s `steering`),
  - `v` = throttle (mapped from dataset’s `throttle`),
  consistent with the training GUI’s `u <- steering`, `v <- throttle` mapping.

If anything fails (no interpreter, no frame, missing numpy/cv2, or exceptions), it returns `None` and autopilot falls back to current control state.

---

## 3. control_api: background `autopilot_step`

### File: `control_api.py`

#### 3.1 New import

```python
from model_manager import get_model_name
from autopilot import predict_uv_from_camera
```

#### 3.2 New function: `autopilot_step(camera)`

Inserted **after** `handle_control_post(...)`:

```python
def autopilot_step(camera):
    """Background step called from /api/status to run the model in auto modes.

    - In manual mode: does nothing.
    - In auto_steer: model controls steering only; throttle remains user-set.
    - In autopilot: model controls both steering and throttle.
    """
    with control_lock:
        mode = control_state.get("mode", "manual")
        if mode not in ("auto_steer", "autopilot"):
            return

        # Ask the TFLite model (if any) for predicted (u, v) = (steering, throttle)
        uv = predict_uv_from_camera(camera)
        if uv is None:
            return

        u, v = uv

        steering = float(u)
        if mode == "auto_steer":
            throttle = float(control_state.get("throttle", 0.0))
        else:  # autopilot
            throttle = float(v)

        # Safety clamp
        steering = max(-1.0, min(1.0, steering))
        throttle = max(0.0, min(1.0, throttle))

        control_state["steering"] = steering
        control_state["throttle"] = throttle
        control_state["last_update"] = time.time()

        motor.update(
            steering=control_state["steering"],
            throttle=control_state["throttle"],
            mode=control_state["mode"],
        )

        # Record what actually got sent to the motors
        record_step(recorder, camera, control_state)
```

Notes:

- **Manual mode**: early return → no change.
- **auto_steer**:
  - Uses model’s `u` for steering,
  - Keeps throttle from previous user input (joystick/slider),
  - Clamps steering ∈ [-1, 1], throttle ∈ [0, 1].
- **autopilot**:
  - Uses both `u` (steering) and `v` (throttle) from the model,
  - Same clamping.
- Every autopilot step also:
  - Updates `last_update`,
  - Calls `motor.update(...)`,
  - Calls `record_step(...)`, so recordings capture the **actual** commands used to move the car.

`handle_control_post(...)` itself remains unchanged:

- It still:
  - Applies incoming JSON steering/throttle/mode,
  - Updates motors,
  - Records a step.
- The autopilot step runs **in addition**, driven by `/api/status` (see below), so there is no behaviour break in manual mode.

---

## 4. server: autopilot tick on `/api/status`

### File: `server.py`

#### 4.1 Import

```python
from control_api import handle_control_post, toggle_recording, get_status, autopilot_step
```

#### 4.2 Status route

Replaced:

```python
@app.route("/api/status", methods=["GET"])
def api_status():
    return jsonify(get_status())
```

with:

```python
@app.route("/api/status", methods=["GET"])
def api_status():
    # Run one background autopilot step (if in auto_steer/autopilot mode)
    autopilot_step(camera)
    return jsonify(get_status())
```

Because the frontend already polls `/api/status` every ~500 ms, this gives us a **natural periodic tick** for:

- Running the model on the latest camera frame,
- Updating the motors and status in auto modes,
- Recording the resulting actions.

Manual mode behaviour is unchanged (autopilot_step early-return).

---

## 5. Behaviour summary

### Manual mode

- Joystick behaviour is unchanged compared to `0_1_9`:
  - Drag pad controls steering in [-1, 1] and throttle in [0, 1].
  - On release, steering=0, throttle=0, a stop packet is sent.
- `/api/control` updates control_state and motors directly.
- `/api/status` just reports current state; `autopilot_step` returns immediately.

### Auto Steer mode

- Mode dropdown set to **auto_steer**.
- User still sets throttle (e.g. by moving joystick upwards once, then releasing).
- Every `/api/status` poll (~2 Hz if 500 ms, or as configured) runs:

  1. Grab latest camera frame.
  2. Run the active TFLite model → (u, v).
  3. Apply:
     - `steering = u`,
     - `throttle = (user throttle)`.
  4. Clamp, call `motor.update(...)`, record step.

- Status bar & Mode panel show **current steering/throttle/mode/model** based on these updated values.

### Autopilot mode (self driving)

- Mode dropdown set to **autopilot**.
- Joystick input becomes optional (model drives both steering and throttle).
- Every `/api/status` poll:

  - Same as auto_steer, but now:
    - `steering = u`,
    - `throttle = v` (model output).

- Recording captures the model-driven run (useful for later analysis).

### Recording

- Recorder code (`data_recorder.py` and `recorder_step.py`) is untouched.
- Each time either:
  - `/api/control` is called (manual input), or
  - `autopilot_step()` runs,
- A record is written with:
  - `image` path,
  - `steering`, `throttle`, `mode`,
  - `timestamp`.

This remains compatible with the PC training GUI:
- `u <- steering`
- `v <- throttle`

---

If you want to change the update frequency of autopilot, adjust the frontend’s polling interval for `/api/status` (currently `setInterval(pollStatus, 500)` in `ui_script.py`).