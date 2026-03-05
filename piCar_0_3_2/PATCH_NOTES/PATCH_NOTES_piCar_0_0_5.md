
# PATCH_NOTES_piCar_0_0_5.md

## Summary

This patch introduces **real Donkey-style recording** on the Pi and fixes
the **manual drag joystick** so the full square is usable and throttle
behaves as expected.

Base version: `piCar_0_0_4`  
New version:  `piCar_0_0_5`

---

## 1. Data recording (data_recorder.py)

- Replaced the old placeholder `DataRecorder` with a full implementation
  that writes Donkey-compatible sessions under `data/raw/`:

  ```text
  data/raw/
      YYYYMMDD-HHMMSS_PICAR/
          images/
              000001.jpg
              000002.jpg
              ...
          index.jsonl
          session.yaml
          summary.json
  ```

- Each record:
  - Captures the current JPEG frame from the Pi camera
  - Decodes and saves it as `images/000001.jpg`, `000002.jpg`, ...
  - Appends a JSON line to `index.jsonl` with keys:

    ```json
    {
      "frame": 1,
      "ts_ms": 1700000000000,
      "image": "images/000001.jpg",
      "mode": "manual",
      "u": 0.12,
      "v": 0.45,
      "crop": {"top": 0, "bottom": 0},
      "resize": [160, 80]
    }
    ```

- `toggle()` now starts/stops a recording session, creating a new
  timestamped folder on each start and updating `summary.json` with the
  number of records when stopping.

- Recording rate is throttled using `min_interval` (default ~10 Hz).

---

## 2. Joystick drag pad (ui_script.py)

- Replaced the previous **circular** joystick mapping with a **full square**
  mapping in `updateFromPoint(x, y)`:

  - `steering = (relX - 0.5) * 2` where `relX ∈ [0, 1]`
  - `throttle = 1 - relY` where `relY ∈ [0, 1]`

- Behaviour:

  - Entire drag area is active (no circular clamp)
  - **Bottom edge → throttle = 0**
  - **Top edge → throttle = 1**
  - Center → `steering ≈ 0`

- The on-screen dot and speed display follow the new mapping, and the
  values are sent to `/api/control` just like before.

---

## 3. Preserved from 0_0_4

The following UI improvements from `piCar_0_0_4` are preserved:

- Taller Manual Drag Control panel
- Recording Control panel at 3 grid rows tall
- Recording status shown with a **red/grey dot** indicator
- Thicker center grid lines in the joystick area

---

## 4. Files changed

- `data_recorder.py`
- `ui_script.py` (only the `updateFromPoint` function inside the embedded JS)
- Added `PATCH_NOTES_piCar_0_0_5.md`
