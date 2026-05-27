# PiSD

`PiSD_0_8_0` full stable v8 package — current stable rollback baseline for future PiSD work.

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behaviour patterns, but PiServer files must not be overwritten by PiSD experiments.

Future bug-fix patches after this package should use `PiSD_0_8_x_patch` naming unless a newer stable line is promoted.

## Current version

`PiSD_0_8_0` — full stable package built from `PiSD_0_7_0` plus accepted patches `0_7_1` through `0_7_3`.

Use `PiSD_0_8_0` as the rollback point for future PiSD work unless a newer stable line is promoted.

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
- Additional overlay tuning values are exposed for sampling, wheelbase, steering response, curvature, width, projection, depth, and turn taper.
- Screenshots and continuous recordings include current overlay settings for future piTrainer redraw.
- Clear Start camera / Live stream / Stop camera / STOP motors / Refresh status behaviour.
- Status-only refresh that does not start the camera or send motor commands.
- Page-leave motor fail-safe stop.
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
- New Motor Tuning page at `/motor-tuning` runs short straight/turn/custom timed commands through the same motor algorithm, then stops automatically.
- Motor Tuning uses linear X steering, a live camera-backed overlay preview, and separate visual overlay calibration controls so the drawn path can be tuned to match the real car motion.
- Dashboard is labelled as a legacy/development comparison shell, with stale speed limits raised to full-scale to avoid conflicting with current Manual Drive limits.
- Default OV5647 camera profile code includes the attempted `03_request_awb_off_lock` request/PIL RGB visual profile and safe runtime migration. This still needs real Pi confirmation if colour does not match the earlier 03/91 diagnostic captures on a specific camera.

This stable baseline keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.

## Motor tuning workflow

Open `/motor-tuning` from the front page when calibrating the real car motion against the visual overlay.

Use the page in this order:

1. Lift the wheels or clear a safe test area, then tick both safety boxes before real motor output.
2. Run a short Straight travel test to confirm speed and left/right balance.
3. Run a short Turn test for left and right curves at a known speed and duration.
4. Use the drag pad/timed tests knowing steering X is linear: `x = 0.5` gives a half-tight turn, and `x = 1.0` gives the tightest non-pivot turn.
5. Adjust overlay values, especially `turn_rate_visual_scale` and `curve_response`, when the real car motion is correct but the drawn predicted path does not match the observed turn on the live camera frame.
6. Save overlay tuning; the values are stored under `manual_drive.overlay` and are also recorded in screenshots/recordings for future piTrainer redraw.

The timed tuning endpoint is `/api/motor/tune-run`. It uses the same `MotorService.update()` mapping as Manual Drive and AI Mode, waits for the selected duration, and then sends STOP in a `finally` path. Real hardware movement still requires live safety acknowledgement and `enable_motor_output`.

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
copy model into PiSD/models/
        ↓
AI Mode loads model → predicts steering/throttle → safety limiter → motor service
```

Supported model file discovery currently includes:

```text
.tflite, .keras, .h5, .onnx, .pt
```

Runtime inference is implemented first for `.tflite` when `tflite_runtime` or TensorFlow Lite support is installed, and for `.keras`/`.h5` when TensorFlow is installed. `.onnx` and `.pt` files are listed so the UI can see them, but they are not runnable until a future backend is added.

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

`PiSD_0_8_0` is the stable rollback baseline before future `0_8_x` patches.

It includes the tested service foundation from earlier baselines plus the accepted v6, v7, and v8 Manual Drive, recording, overlay, AI Mode, steering algorithm, motor tuning, safety-policy, and validation cleanup patch lines.

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
unzip -o PiSD_0_8_0.zip
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
- Camera setting source-of-truth is still duplicated between backend defaults, service dataclass, UI forms, and diagnostic scripts. If the OV5647 colour still does not match the earlier 03/91 diagnostic result on real hardware, that should be a future `0_8_x` camera patch.
