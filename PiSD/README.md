# PiSD

`PiSD_0_9_0` full stable v9 package — current stable rollback baseline for future PiSD work.

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behaviour patterns, but PiServer files must not be overwritten by PiSD experiments.

Future bug-fix patches after this package should use `PiSD_0_9_x_patch` naming unless a newer stable line is promoted.

## Current version

`PiSD_0_9_0` — full stable package built from `PiSD_0_8_0` plus accepted patches `0_8_1` through `0_8_11`, plus Manual Drive keyboard control.

Use `PiSD_0_9_0` as the rollback point for future PiSD work unless a newer stable line is promoted.

Included accepted work:

- Manual Drive overlay toggle on the Manual Drive page.
- Road-guide overlay presentation using a filled drivable path corridor plus two thin left/right road-edge guide lines.
- Straight overlay forms a perspective trapezium; turning overlay uses sampled kinematic-style path geometry.
- Road edges are offset using local tangent normals, so inner and outer sides bend more naturally.
- Shared overlay geometry helper used by both Manual Drive and AI Mode.
- Corrected overlay left/right turn direction in the shared helper.
- Reverse-motion overlay drawing hidden; reverse steering policy remains same-sign.
- Overlay settings now use numeric inputs in a popup instead of sliders/drop-down controls.
- Overlay values are no longer clamped back to old slider ranges when typed or saved.
- Manual Drive overlay tuning is reduced to seven visual-only controls, and the values are accepted without old UI min/max caps.
- Screenshots and continuous recordings include `overlay_settings.json` and `overlay_settings_history.jsonl` for future piTrainer redraw.
- Clear Start camera / Live stream / Stop camera / STOP motors / Refresh status behaviour.
- Status-only refresh that does not start the camera or send motor commands.
- Page-leave motor fail-safe stop.
- Manual Drive now supports keyboard driving: ↑/↓ adjust live throttle by `0.05` per press, holding ←/→ ramps steering by full scale in `0.8 s`, and Space stops.
- Preview idle start, FPS estimate, frame-age display, stale-frame warning, and guarded preview metrics loop.
- Recording/snapshot selected-folder details, safer download/delete button states, and hardened backend folder-id validation.
- Manual Drive recordings include trainer-friendly `labels.jsonl` beside full `records.jsonl` metadata.
- AI Mode page at `/ai-mode`, replacing the earlier scripted Autopilot foundation.
- Legacy `/autopilot` path is retained only as a retired compatibility/redirect path to AI Mode.
- AI Mode model listing/loading from `PiSD/models/` and a guarded safety layer between AI predictions and motor output.
- AI Mode max throttle and fixed throttle controls allow full-scale `1.00`.
- AI Mode preview reuses the Manual Drive preview-frame design and draws the road-guide overlay from the model prediction after the safety limiter.
- AI steering-only mode keeps fixed throttle while driving straight.
- AI motor-output enable is live/session-only and is not persisted across reloads.
- Manual Drive backend now enforces the saved max speed limit in `/api/control/manual`.
- Hardware Manual Drive API commands require live safety and motor-output acknowledgement.
- Manual Drive no longer overrides saved motor `steer_mix`; motor mixing is controlled by the motor settings.
- Default motor steering mode is now `turn_rate`: left/right input controls curve tightness while up/down controls travel speed along that curve. The older `arcade_mix` behaviour remains selectable as a fallback.
- The Manual Drive and AI Mode overlays are visual-only calibration layers. They are manually tuned to match the real camera view and real car motion instead of being driven by motor tuning values.
- Motor Tuning at `/motor-tuning` has been cleared in patch `0_8_7` so the calibration workflow can be rebuilt from a clean page. The backend motor service, linear X steering, and overlay settings remain available for the next design.
- Dashboard is labelled as a legacy/development comparison shell, with stale speed limits raised to full-scale to avoid conflicting with current Manual Drive limits.
- Default OV5647 camera profile code includes the attempted `03_request_awb_off_lock` request/PIL RGB visual profile and safe runtime migration. This still needs real Pi confirmation if colour does not match the earlier 03/91 diagnostic captures on a specific camera.

This stable baseline keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.

## Motor tuning workflow

Patch `0_8_7` intentionally clears the `/motor-tuning` page. The previous safety, timed motion, live preview, overlay controls, motor settings, and log panels were removed so the page can be rebuilt cleanly.

The backend pieces remain available for the next design:

- `/api/motor/tune-run` still runs a timed command through the normal motor steering algorithm and stops in a `finally` path.
- Linear X steering remains active in `MotorService`: `x = 0.5` gives a half-tight turn and `x = 1.0` gives the tightest non-pivot turn.
- Overlay calibration remains visual-only and separate from motor output.

Until the new tuning page is rebuilt, use Manual Drive and backend/API checks for live car testing.

## Manual Drive keyboard control

Manual Drive supports keyboard control after motor output is enabled and the browser focus is not inside an input field:

```text
Arrow Up    throttle +0.05 per press
Arrow Down  throttle -0.05 per press
Hold Left   steering ramps toward -1.00 at full scale in 0.8 s
Hold Right  steering ramps toward +1.00 at full scale in 0.8 s
Space       STOP motors and clear keyboard throttle/steering
```

Keyboard commands use the same `/api/control/manual` path as the drag pad, so they keep the same safety acknowledgement, intended-output display, recording labels, and linear X steering behaviour.

## AI Mode workflow

PiSD AI Mode follows a DonkeyCar-style behavioural-cloning workflow while keeping PiSD's own lightweight web UI and motor service:

```text
Manual Drive recording
  camera frame + steering + throttle + overlay settings
        ↓
recordings/.../frames + records.jsonl + labels.jsonl
        ↓
train/export model on PC or trainer tool
        ↓
upload/copy model into PiSD/models/
        ↓
AI Mode loads model → predicts steering/throttle → safety limiter → motor service
```

Supported model file discovery currently includes:

```text
.tflite, .keras, .h5, .onnx, .pt
```

Runtime inference is implemented for piTrainer-exported `.tflite` models when a TFLite runtime backend is installed, and for piTrainer-exported `.keras`/`.h5` models when TensorFlow is installed. PiSD reads piTrainer's named `steering` and `throttle` outputs, including Keras dict/list outputs and TFLite one-tensor or two-tensor outputs. `.onnx` and `.pt` files are listed so the UI can see them, but they are not runnable until a future backend is added.

The TFLite loader tries these Python backends in order:

```text
tflite_runtime.interpreter
ai_edge_litert.interpreter
tensorflow.lite.Interpreter
```

The **Load trained model** panel can upload a model from the browser to `PiSD/models/` and can delete a selected model from the Pi. Upload uses a safe filename and appends a timestamp if the same filename already exists. The panel also shows runtime diagnostics. If `Backend` shows `load_failed` or `Runtime` shows `TFLite missing`, install a compatible TFLite backend in the same Python environment that runs PiSD, restart PiSD, and click **Load model** again. PiSD includes helper commands for this:

```bash
cd ~/PiDrive/PiSD
python3 scripts/install_ai_runtime.py --runtime tflite-runtime
python3 scripts/check_ai_runtime.py
```

If `tflite-runtime` is unavailable on that Pi/Python combination, try:

```bash
python3 scripts/install_ai_runtime.py --runtime ai-edge-litert
python3 scripts/check_ai_runtime.py
```

See `docs/AI_RUNTIME_SETUP.md` for the full runtime setup note.

AI reverse steering policy remains **same sign**: when throttle is negative, PiSD does not flip the steering value. The current road-guide overlay does not draw reverse motion.

AI drive is blocked unless:

- a runnable model is loaded;
- the safety acknowledgement is checked;
- motor output is enabled for the current live session;
- the AI safety limiter clamps the prediction to saved max steering/throttle limits.

Focused validation:

```bash
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_ai_drive_service.py
```

## Recording data structure

Continuous Manual Drive recording sessions are stored under:

```text
PiSD/recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS_manual_drive_xxxxxxxx/
  frames/
  manifest.json
  records.jsonl
  labels.jsonl
```

Single captures are stored under:

```text
PiSD/recordings/single_captures/YYYY-MM-DD/
  frames/
  manifest.json
  records.jsonl
  labels.jsonl
```

For piTrainer, use `labels.jsonl` first:

```text
image → steering, throttle, overlay_settings
```

Use `records.jsonl` only for full debug metadata, filtering, or advanced training options. If a frame-level overlay value is missing, fall back to `records.jsonl`, then `manifest.json`, then trainer defaults.

## Stable baseline notes

`PiSD_0_9_0` is the stable rollback baseline before future `0_9_x` patches.

It includes the tested service foundation from earlier baselines plus the accepted v6, v7, v8, and v9 Manual Drive, recording, overlay, AI Mode, steering algorithm, motor tuning, keyboard-control, safety-policy, and validation cleanup patch lines.

Real wheel direction is intentionally configurable through settings because different cars may be wired differently. Use lifted-wheel motor channel tests before driving on the floor.

## Folder layout

```text
PiSD/
├── PiSD.py                       # main launcher
├── README.md                     # install/run overview
├── requirements.txt              # single pip dependency file
├── config/
│   └── defaults.json             # safe default camera/motor settings
├── pisd/
│   ├── __init__.py               # PiSD package version
│   ├── app.py                    # Flask GUI/API wiring
│   ├── web/                      # templates and static assets
│   ├── core/                     # errors/settings/value helpers
│   └── services/                 # camera, motor, recording, AI services
├── scripts/                      # validation and diagnostic scripts
├── test_outputs/                 # generated test captures/log-friendly outputs
├── docs/                         # architecture, testing, settings, and stable baseline notes
└── PATCH_NOTES/                  # historical patch notes and stable release notes
```

## Install / run on Raspberry Pi

From the PiDrive root:

```bash
cd ~/PiDrive
unzip -o PiSD_0_9_0.zip
cd ~/PiDrive/PiSD
python3 -m pip install --break-system-packages -r requirements.txt
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open from another device on the same network:

```text
http://<pi-ip>:5050
```

After applying the package over an older browser session, hard refresh the page:

```text
Ctrl + F5
```

## Standard validation

Container/desktop static validation:

```bash
python3 -m compileall -q pisd scripts
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
```

Pi hardware validation should also include:

```bash
python3 scripts/test_camera_service.py --hardware
python3 scripts/test_motor_service.py --hardware
python3 scripts/test_motor_channels.py --hardware
```

## Known limits / next steps

- Full Flask route/API tests were not run in the packaging container because Flask is not installed there.
- Real Raspberry Pi camera and motor hardware were not tested in the packaging container.
- Dashboard remains a labelled legacy/development comparison shell; Manual Drive and AI Mode are the active control pages.
- Shared API/status helper logic is still duplicated across some frontend files and can be centralised later.
- piTrainer still needs a matching update to redraw the overlay from saved `overlay_settings` metadata.
- Camera setting source-of-truth is still duplicated between backend defaults, service dataclass, UI forms, and diagnostic scripts. If the OV5647 colour still does not match the earlier 03/91 diagnostic result on real hardware, that should be a future `0_9_x` camera patch.
