# PiSD

`PiSD_0_5_8_patch` — overlay curve presentation refinement patch built forward from the PiSD_0_5_0 stable baseline plus the accepted AI Mode work.

Stable v5 is built from `PiSD_0_4_0` plus accepted patches `PiSD_0_4_1` through `PiSD_0_4_10`. It includes the v4 camera/motor/error-reporting foundation, responsive GUI, Manual Drive page, recording/snapshot workflow, and all accepted v4 patch-line improvements: code cleanup, Manual Drive preview overlay, predicted steering/throttle arc, overlay calibration/debugging, command-safety consistency, preview FPS/stale-state reliability, and safer recording/snapshot folder management.

Future bug-fix patches after this stable package should use `PiSD_0_5_x_patch` naming unless a newer stable line is promoted.

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behavior patterns, but PiServer files must not be overwritten by PiSD experiments.

## Current version

`PiSD_0_5_8` — current patched working version when this patch is applied after the accepted AI Mode patch line.

This package consolidates the accepted `0.4.x` work into a full installable `PiSD/` folder rather than a patch-only zip. It should be used as the clean rollback point before starting future `0_5_x` patches.

Included accepted work:

- Manual Drive overlay toggle on the Manual Drive page.
- Sampled predicted-arc overlay based on throttle and steering.
- Overlay calibration controls for path length, curve strength, opacity, and path width.
- Overlay/source debug values for steering, throttle, left/right output, and stopped/manual/live source.
- Clearer Start camera / Live stream / Stop camera / STOP motors / Refresh status behavior.
- Status-only refresh that does not start the camera or send motor commands.
- Page-leave motor fail-safe stop.
- Preview idle start, FPS estimate, frame-age display, stale-frame warning, and guarded preview metrics loop.
- Recording/snapshot selected-folder details, safer download/delete button states, and hardened backend folder-id validation.
- AI Mode page at `/ai-mode`, replacing the earlier scripted Autopilot foundation.
- Manual Drive recordings now include trainer-friendly `labels.jsonl` beside full `records.jsonl` metadata.
- AI Mode model listing/loading from `PiSD/models/` and a guarded safety layer between AI predictions and motor output.
- AI Mode max throttle and fixed throttle controls now allow full-scale `1.00`, matching Manual Drive motor command range.
- AI Mode reuses Manual Drive panel/topbar/button styling for a consistent interface.
- AI Mode preview now reuses the Manual Drive preview-frame design and includes an AI safe-command road-guide overlay drawn from the model prediction after the safety limiter.
- Default OV5647 camera profile now uses the tested `03_request_awb_off_lock` request/PIL RGB visual profile for preview and training capture.
- Reverse driving currently uses Option A: negative throttle keeps the same steering sign in motor output and preview overlays.

- Manual Drive and AI Mode overlays now use a road-guide presentation: two left/right road-edge lines form a perspective trapezium when straight and bend by different amounts when turning.
- PiSD 0.5.9 hides reverse-motion drawing in the overlay and removes the car-rectangle marker from the preview guide.

This stable baseline keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.

## AI Mode workflow

PiSD AI Mode follows a DonkeyCar-style behavioural-cloning workflow while keeping PiSD's own lightweight web UI and motor service:

```text
Manual Drive recording
  camera frame + steering + throttle
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

AI reverse steering policy in this patch is **same sign**: when throttle is negative, PiSD does not flip the steering value. This matches Manual Drive and MotorService mixing while still drawing the overlay path backward.

AI drive is blocked unless:

- a runnable model is loaded;
- the safety acknowledgement is checked;
- motor output is enabled;
- the AI safety limiter clamps the prediction to saved max steering/throttle limits.

Focused validation:

```bash
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_ai_drive_service.py
```

## Stable baseline notes

`PiSD_0_5_0` is the stable rollback baseline before future `0_5_x` patches.

It includes the tested camera/motor/error-reporting foundation from earlier baselines plus the accepted v4 Manual Drive overlay, safety, preview-reliability, and file-management patch line.

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
│   ├── web/
│   │   ├── templates/main_dashboard.html
│   │   ├── templates/testing_server.html
│   │   ├── templates/panel_testing.html
│   │   └── static/               # main dashboard, testing GUI, and panel-lab CSS/JS
│   ├── core/
│   │   ├── errors.py             # shared error codes/reporting helpers
│   │   └── value_utils.py        # clamp/parse helpers
│   └── services/
│       ├── camera_service.py     # Picamera2 + simulation camera service
│       └── motor_service.py      # RPi.GPIO-style + simulation motor service
├── scripts/
│   ├── check_error_reporting.py  # error-code/reporting schema check
│   ├── check_service_imports.py  # import/default/app wiring check
│   ├── test_api_endpoints.py     # Flask test-client API smoke test
│   ├── test_camera_service.py    # camera frame capture test
│   ├── diagnose_camera_color.py   # real camera colour/AWB diagnostic captures
│   ├── test_live_http_api.py     # HTTP test against running server
│   ├── run_standard_validation.py # standard OK/FAIL validation checklist
│   ├── test_main_dashboard.py    # actual dashboard shell validation
│   ├── test_testing_server_gui.py # temporary API/settings GUI validation
│   ├── test_panel_testing_page.py # panel lab validation
│   ├── test_panel_api_contracts.py # panel API contract validation
│   ├── test_motor_channels.py    # one-by-one motor calibration test
│   └── test_motor_service.py     # motor mapping and optional GPIO test
├── test_outputs/                 # generated test captures/log-friendly outputs
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── ERROR_CODES.md
│   ├── FUTURE_CODE_RULES.md
│   ├── DIRECTORY_GUIDE.md
│   ├── GUI_FUNCTION_SPEC.md
│   ├── HARDWARE_SERVICES.md
│   ├── MOTOR_CALIBRATION.md
│   ├── STABLE_BASELINE.md
│   ├── TEST_PLAN.md
│   ├── TESTING_SERVER_GUI.md
│   └── PANEL_TESTING_GUI.md
└── PATCH_NOTES/
    ├── PATCH_NOTES_PiSD_0_0_0.md
    ├── PATCH_NOTES_PiSD_0_0_1.md
    ├── PATCH_NOTES_PiSD_0_0_2.md
    ├── PATCH_NOTES_PiSD_0_0_3.md
    ├── PATCH_NOTES_PiSD_0_0_4.md
    ├── PATCH_NOTES_PiSD_0_0_5.md
    ├── PATCH_NOTES_PiSD_0_0_6.md
    ├── PATCH_NOTES_PiSD_0_1_0.md
    ├── PATCH_NOTES_PiSD_0_1_1.md
    ├── PATCH_NOTES_PiSD_0_1_2.md
    ├── PATCH_NOTES_PiSD_0_2_0.md
    ├── PATCH_NOTES_PiSD_0_2_1.md
    ├── PATCH_NOTES_PiSD_0_2_2.md
    ├── PATCH_NOTES_PiSD_0_2_3.md
    ├── PATCH_NOTES_PiSD_0_2_4.md
    └── PATCH_NOTES_PiSD_0_2_5.md
```

## Install

From inside `PiSD/`:

```bash
python -m pip install -r requirements.txt
```

On Raspberry Pi OS, install camera packages with `apt` first when testing real camera hardware:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera python3-opencv
```


## Main dashboard GUI shell

Run the PiSD server:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open the front page:

```text
http://<pi-ip>:5050/
```

Open AI Mode directly:

```text
http://<pi-ip>:5050/ai-mode
```

`PiSD_0_2_5` made `/` the first real dashboard shell. It includes these initial panels:

```text
System Status
Camera Preview
Manual Drive
Motor Channel Calibration
Safety Stop
Error Monitor
Action Log
```

Motor movement controls are locked by default. The dashboard requires the user to tick the lifted-wheels safety checkbox before manual drive or channel-test controls become active. STOP buttons remain active at all times.

Focused dashboard validation:

```bash
python3 scripts/test_main_dashboard.py
```

Static-only version for packaging machines without Flask:

```bash
python3 scripts/test_main_dashboard.py --static-only
```

## Testing server GUI

Run the temporary browser-based API/settings tester:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/
http://<pi-ip>:5050/testing
```

Use this page to check camera settings, motor settings, one-by-one motor channel tests, custom API calls, STOP, and visible `PISD-*` response codes before building the final PiServer-style GUI.

`PiSD_0_2_2` also adds a **Run safe smoke test** button on the testing page. It runs safe browser-side API checks for status, manifest, camera start/frame/apply, motor config/apply, unarmed motor-channel safety, and STOP. It does not arm real motor output.

The GUI files are:

```text
PiSD/pisd/web/templates/testing_server.html
PiSD/pisd/web/static/css/testing_server.css
PiSD/pisd/web/static/js/testing_server.js
```

Real motor output remains locked unless the page sends `enable_motor_output: true`; keep wheels lifted.

## Panel testing GUI

Run the same PiSD server, then open the panel lab:

```text
http://<pi-ip>:5050/panel-testing
```

This page is a layout and component test bed for the future actual GUI. The panels are remade for the new lab and are not copied from the older API testing page.

It lists the planned final-GUI panels:

```text
System Status
Camera Preview
Camera Settings
Motor Settings
Motor Channel Calibration
Manual Drive
Safety Stop
Error Monitor
API Inspector
Validation Checklist
Recording and Dataset
Model and Lane Runtime
```

Use the left settings column to test every panel under different environments:

```text
theme
layout mode
phone/tablet/laptop/large-monitor width presets
compact/standard/large/stress panel sizes
density
font scale
panel gap
corner radius
border/shadow strength
minimum panel width
preview aspect ratio
```

Focused panel-lab validation:

```bash
python scripts/test_panel_testing_page.py
```

Static-only version:

```bash
python scripts/test_panel_testing_page.py --static-only
```

## Run in safe simulation mode

Simulation mode is the default so the GUI and APIs can be developed on a PC without touching real motors.

```bash
cd PiSD
python PiSD.py
```

Open:

```text
http://127.0.0.1:5050
```

Status-only check:

```bash
python PiSD.py --status-only
```


## Run on the Raspberry Pi LAN

```bash
python PiSD.py --host 0.0.0.0 --port 5050
```

## Enable real hardware adapters

Real camera/motor adapters are only enabled when `--hardware` is used:

```bash
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

This is intentional. It prevents accidental motor activation while developing the GUI on a PC.

## Service testing scripts

All scripts are run from inside `PiSD/`.


Standard all-in-one validation checklist. This prints simple `OK` / `FAIL` lines with PiSD codes and writes `test_outputs/standard_validation/summary.json`. It now includes static testing-GUI file checks and stronger local API contract checks when Flask is available:

```bash
python scripts/run_standard_validation.py
```

Real camera/GPIO adapter check without moving motors:

```bash
python scripts/run_standard_validation.py --hardware
```

Real camera plus real one-by-one motor output check. Lift the wheels first:

```bash
python scripts/run_standard_validation.py --hardware --enable-motor-output
```


Focused testing-GUI validation. This checks the testing page files, smoke-test controls, static asset route contract, manifest endpoint, invalid motor input, 404 error code, and safe unarmed motor behaviour:

```bash
python scripts/test_testing_server_gui.py
```

Static-only version, useful on a packaging PC without Flask:

```bash
python scripts/test_testing_server_gui.py --static-only
```

Focused panel-testing GUI validation. This checks the flexible panel lab files, planned panel registry, style controls, size controls, responsive rules, route, static assets, and manifest:

```bash
python scripts/test_panel_testing_page.py
```

Static-only version:

```bash
python scripts/test_panel_testing_page.py --static-only
```

Error-code/reporting schema check:

```bash
python scripts/check_error_reporting.py
```

Basic import and service wiring check:

```bash
python scripts/check_service_imports.py
```

Camera service check. In simulation mode this writes a generated frame to `test_outputs/`:

```bash
python scripts/test_camera_service.py
```

Real camera service check on the Pi:

```bash
python scripts/test_camera_service.py --hardware
```


Camera colour diagnostic on the Pi. Use this if the real camera opens but the saved colour looks wrong:

```bash
python scripts/diagnose_camera_color.py --hardware
```

This saves comparison files under `test_outputs/camera_color/`. `03_request_awb_off_lock.jpg` is the preferred preview/training baseline after the OV5647 colour comparison. When array diagnostics are enabled, `91_array_rgb` is the known-good raw array reference.

Raw array colour-order check. Use RGB first because the `91_array_rgb` diagnostic was confirmed correct:

```bash
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb --output test_outputs/array_rgb.jpg
```

API route check without starting a network server:

```bash
python scripts/test_api_endpoints.py
```

Motor mapping check in simulation mode:

```bash
python scripts/test_motor_service.py
```

Optional real motor GPIO output check on the Pi. Use only when the wheels are lifted and the car is safe:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

One-by-one motor channel calibration. This tests left/right motors separately, raw `direction_1`/`direction_2`, multiple speeds, and stop-after-each-step:

```bash
python scripts/test_motor_channels.py
python scripts/test_motor_channels.py --hardware --enable-motor-output
```

Live HTTP check against a running PiSD server:

```bash
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

The live HTTP script does not send movement commands unless this flag is added:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050 --enable-motor-output
```

## API endpoints

```text
GET  /api/status
GET  /api/errors
POST /api/errors/clear
POST /api/camera/start
POST /api/camera/stop
GET  /api/camera/config
POST /api/camera/apply
GET  /api/camera/frame.jpg
GET  /video_feed
GET  /api/motor/config
POST /api/motor/apply
POST /api/motor/test-channel
POST /api/control/manual
POST /api/control/stop
```

## Error detection and reporting rule

All current and future PiSD code should report problems with a structured PiSD code. JSON API responses should include at least:

```json
{"ok": true, "code": "PISD-OK-000", "message": "OK"}
```

Failures should include a non-OK code, message, component, timestamp, and diagnostic context. See:

```text
docs/ERROR_CODES.md
docs/FUTURE_CODE_RULES.md
```

Useful diagnostics:

```bash
python scripts/check_error_reporting.py
```

At runtime:

```text
/api/status
/api/errors
```

## Hardware service notes

Camera service:

- uses Picamera2 when `--hardware` is enabled and Picamera2 is available
- falls back to a simulated changing frame when Picamera2 is unavailable
- exposes current JPEG frames through `/api/camera/frame.jpg`
- defaults to the Picamera2 request/PIL JPEG path for better colour fidelity in preview images
- keeps the raw array/OpenCV path available for computer-vision diagnostics via `capture_source: "array"`
- exposes MJPEG stream through `/video_feed`

Motor service:

- follows the existing PiServer differential-drive mapping style
- defaults to PiServer-like BCM pins: left `(17, 27)`, right `(22, 23)`
- uses RPi.GPIO-style PWM when `--hardware` is enabled and GPIO is available
- otherwise logs simulated motor outputs
- always provides `/api/control/stop`

## Development rule

Keep PiSD as a clean test path. Do not replace `PiServer/` until PiSD has been tested enough and the user explicitly asks for merge/replacement.

---

## PiSD 0.0.5 camera setting tests

PiSD now exposes camera settings through the service, API, and scripts. The default visual preview path is:

```json
"capture_source": "request"
```

Keep this for GUI preview and colour checking. The raw `array` path remains available for future computer-vision work. Use `array_color_order: "rgb"` because the `91_array_rgb` diagnostic was confirmed correct, while the earlier auto/BGR array outputs were wrong on the OV5647 test.

### Capability dump

```bash
python3 scripts/dump_camera_capabilities.py --hardware
```

### Single setting tests

```bash
python3 scripts/test_camera_service.py --hardware --capture-source request
python3 scripts/test_camera_service.py --hardware --width 640 --height 360 --fps 15 --preview-quality 80 --buffer-count 4 --no-queue
python3 scripts/test_camera_service.py --hardware --manual-exposure --exposure-us 8000 --analogue-gain 1.5
python3 scripts/test_camera_service.py --hardware --awb-mode daylight
python3 scripts/test_camera_service.py --hardware --awb-off --colour-gains 1.8,1.2
python3 scripts/test_camera_service.py --hardware --brightness 0.05 --contrast 1.2 --saturation 1.2 --sharpness 1.1
```

### Matrix test

```bash
python3 scripts/test_camera_settings_matrix.py --hardware
```

Optional raw-array diagnostics:

```bash
python3 scripts/test_camera_settings_matrix.py --hardware --include-array-diagnostics
python3 scripts/diagnose_camera_color.py --hardware --include-array-diagnostics
```

### API settings endpoint

Start the server:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Check camera config and capabilities:

```bash
curl http://127.0.0.1:5050/api/camera/config
curl http://127.0.0.1:5050/api/camera/capabilities
```

Apply camera settings:

```bash
curl -X POST http://127.0.0.1:5050/api/camera/apply \
  -H 'Content-Type: application/json' \
  -d '{"width":640,"height":360,"fps":15,"preview_quality":80,"capture_source":"request"}'
```

All setting failures, ignored values, or unsupported libcamera controls should be reported through PiSD error codes, especially `PISD-CAM-009` and `PISD-CAM-010`.


## Motor calibration

See `docs/MOTOR_CALIBRATION.md`.

## PiSD 0.2.4 panel API contracts

The `/panel-testing` page now tests both panel layout and panel API contracts before the actual GUI server is built.

Run the focused contract check:

```bash
python3 scripts/test_panel_api_contracts.py
```

Hardware-mode check without arming motors:

```bash
python3 scripts/test_panel_api_contracts.py --hardware
```

Start the testing server:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/panel-testing
```

Use these page buttons:

```text
Run structure checks
Run panel API checks
Save preset / Load preset / Export preset / Import preset
```

The contract endpoint is:

```text
GET /api/panel-testing/contracts
```

Expected safe panel API checks should return `PISD-OK-000`, `PISD-MOT-008` for unarmed hardware motor-channel safety refusal, or `PISD-TEST-013` for intentional future placeholders.


## PiSD 0.2.6 front page routing

`PiSD_0_2_6` changes the root route into a mode-selection front page:

- `/` — front page / mode selector
- `/settings` — settings tab for camera and motor setting API checks
- `/testing` — testing tab for API and settings validation
- `/dashboard` — actual dashboard shell from 0.2.5
- `/panel-testing` — panel layout/API contract lab

Every tab/page includes a **Back to Front Page** link so testers can return to the mode selector.

## Live preview FPS testing

For higher live-preview FPS, use the MJPEG stream endpoint:

```text
/video_feed
```

Single-frame snapshots remain available at:

```text
/api/camera/frame.jpg
```

The testing page includes a **Live FPS pipeline test** card:

```text
http://<pi-ip>:5050/testing
```

Useful commands:

```bash
python3 scripts/test_camera_fps.py --hardware --seconds 5 --fps 30 --capture-source array
python3 scripts/test_live_frame_fps.py --base-url http://127.0.0.1:5050 --seconds 5 --mode mjpeg --apply-fast-preview
```

## Panel presentation settings page

PiSD 0.2.8 adds a separate page for tuning panel presentation without changing `/panel-testing`:

```text
http://<pi-ip>:5050/panel-presentation
```

Use it to save compact panel spacing, size, density, and preview aspect settings. These settings apply in the browser across the front page, settings tab, testing tab, dashboard, and panel testing page.

Validation:

```bash
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

## PiSD 0.2.9 manual drive and shared settings update

PiSD 0.2.9 adds a simple user-facing manual drive page:

```text
/manual-drive
```

The front page now includes a **Manual Drive** option. This page is intended for easy car control and includes:

- live camera preview using `/video_feed`
- important runtime status
- manual drive pad
- speed and steer-strength sliders
- always-available STOP buttons
- motor output lock that must be enabled before movement buttons work

The settings tab also saves camera/motor form values in browser storage:

```text
pisd.runtimeSettings.v1
```

Submitting camera or motor settings still applies them through the backend API, so the updated runtime configuration is shared by all tabs that use the same PiSD services.

Panel presentation settings now include more style controls for panel padding, header mode, button size, console height, preview fit, and card accent. They continue to save under:

```text
pisd.panelPresentation.v1
```

Validation:

```bash
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

## PiSD 0.2.10 settings and manual-drive notes

The Settings page now saves shared runtime settings through `/api/settings`. These settings are stored in `config/runtime_settings.json` and loaded by all pages where possible. Browser localStorage is used only as a fallback/cache for immediate styling.

Useful checks:

```bash
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

With the server running:

```bash
python3 scripts/test_settings_persistence.py --base-url http://127.0.0.1:5050
```

Manual Drive now uses a drag pad. It remains locked until the user confirms the wheels/area are safe. Releasing the drag pad sends STOP.

## GUI presentation source of truth

From `PiSD_0_3_4`, GUI presentation is controlled through a shared design system instead of remaking styles on each page:

- `pisd/core/presentation_registry.py` defines defaults and page layout contracts.
- `pisd/web/static/css/pisd_design_system.css` is loaded last on all GUI pages.
- `pisd/web/static/js/panel_presentation_global.js` applies saved settings from `/api/settings`.
- `config/runtime_settings.json` stores user presentation settings.

See `docs/PRESENTATION_DEVELOPMENT.md` before changing page or panel layout.

## Manual Drive capture and recording

The Manual Drive page includes:

- `Capture frame` — saves one camera frame plus metadata.
- `Record` — starts/stops frame recording to an ordered session folder.

Saved data is written under:

```text
PiSD/recordings/
```

Each saved frame has a matching JSONL metadata record containing camera settings, steering, throttle, motor outputs, bias, directions, and max-speed tuning. See `docs/RECORDING_DATA.md`.

Validation:

```bash
python3 scripts/test_recording_service.py
```

## PiSD 0.3.6 notes

- Settings loading now clamps stale saved motor speed limits so `left_max_speed`, `right_max_speed`, and Manual Drive max speed should not return to `1.0`.
- The Manual Drive camera panel shows a visible recording indicator.
- A single-frame capture shows a visible confirmation notice.
- Continuous recordings each use their own folder.
- Single manual captures share one same-day folder: `recordings/single_captures/YYYY-MM-DD/`.
- The shared UI colour palette is documented in `docs/COLOR_PALETTE.md` and defined in `pisd/core/presentation_registry.py` plus `pisd/web/static/css/pisd_design_system.css`.

## PiSD 0.3.7 responsive layout system

PiSD now has a final responsive layout authority:

```text
pisd/web/static/css/pisd_layout_system.css
```

Every GUI page loads this file last, after `pisd_design_system.css`. The saved presentation settings still tune spacing, density, radius, font scale, preview fit, button size, and role weights, but they no longer control safety-critical panel order.

Run the layout contract check with:

```bash
python3 scripts/test_responsive_layout_contract.py --static-only
```

Manual Drive wide layout is fixed as:

```text
status  status
preview drive
preview stop
log     log
```

## PiSD 0.4.0 stable v4 baseline

`PiSD_0_4_0` is the rollback baseline after the accepted `0.3.x` manual-drive, layout, recording, and file-management patches. It should be used before starting future `0.4.x` patch-only work.

Key v4 features include:

- responsive shared GUI layout system
- Manual Drive page with drag-pad control
- run-signal display for intended command and reported motor output
- camera capture and recording controls
- recording/snapshot folder list, zip download, and delete APIs
- persistent settings and shared presentation defaults

