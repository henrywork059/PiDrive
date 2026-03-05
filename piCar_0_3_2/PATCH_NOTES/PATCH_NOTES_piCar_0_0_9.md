
# PATCH_NOTES_piCar_0_0_9.md

## Summary

This patch replaces the complex Donkey-style recorder with a **simple,
easy-to-debug recorder** that still captures all the data needed for
training (image + steering + throttle + mode + timestamp).

- It keeps the original wiring in `control_api.py`:
  `recorder.maybe_record(camera, control_state)`
- It does **not** depend on any specific PC GUI format. The trainer
  can be updated later to read the simple `records.jsonl` format.

Base version: `piCar_0_0_6`  
New version:  `piCar_0_0_9`

---

## 1. Recording format

For each recording session, a new folder is created:

```text
data/records/
    YYYYMMDD-HHMMSS/
        images/
            000001.jpg
            000002.jpg
            ...
        records.jsonl
```

Each line of `records.jsonl` is a single JSON object:

```json
{
  "frame": 1,
  "ts": 1700000000.123,
  "image": "images/000001.jpg",
  "steering": 0.12,
  "throttle": 0.45,
  "mode": "manual"
}
```

This is deliberately simple so the PC trainer can be adapted without
worrying about Donkey-specific fields.

---

## 2. Code structure (`data_recorder.py`)

The recorder module is kept small and simple:

- One main class: `DataRecorder`
- A few clear methods:

  - `start()` — create a new session folder and open `records.jsonl`
  - `stop()` — close the file and end the session
  - `toggle()` — used by `/api/record/toggle`
  - `maybe_record(camera, control_state)` — called on every
    `/api/control` POST from the web UI

Internally, `maybe_record(...)`:

1. Checks if `recording` is `True` and enough time has passed
   (`min_interval`, default ~0.1 s).
2. Grabs a JPEG frame from `camera.get_jpeg_frame()`.
3. Saves it as `images/000001.jpg`, `000002.jpg`, ...
4. Appends a JSON line to `records.jsonl` with steering, throttle,
   mode, timestamp, and image path.

---

## 3. Compatibility

- `control_api.py` does **not** need to change: it still imports
  `DataRecorder` and creates `recorder = DataRecorder()`.
- `handle_control_post(...)` still calls:

  ```python
  recorder.maybe_record(camera, control_state)
  ```

  which now uses the new simple implementation.

- All UI behaviour from earlier patches remains unchanged
  (joystick mapping, panels, red/grey recording dot, etc.).

---

## 4. Files changed

- `data_recorder.py` — rewritten as a small, self-contained recorder
  that produces `data/records/<session>/records.jsonl` + images.
- `PATCH_NOTES_piCar_0_0_9.md` — this file.
