# PiSD

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behavior patterns, but PiServer files must not be overwritten by PiSD experiments.

## Current version

`PiSD_0_2_1` — first patch after v2 baseline, adding the temporary testing server GUI for API/settings validation.

This package is built from stable `PiSD_0_1_0` plus the accepted `PiSD_0_1_1` motor-channel calibration patch and `PiSD_0_1_2` standard validation patch.

This stable baseline keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.


## Stable baseline notes

`PiSD_0_2_0` is the current stable rollback baseline before GUI development. `PiSD_0_2_1` is a patch-only testing GUI layer built on top of that baseline.

It keeps the tested camera/motor/error-reporting foundation from `PiSD_0_1_0`, then adds one-by-one motor channel calibration and the standard OK/FAIL validation script.

Confirmed by Raspberry Pi test logs supplied by the user:

- status/error reporting returns `PISD-OK-000`
- Picamera2 OV5647 hardware capture works
- trusted visual colour reference is `01_request_awb_auto`
- confirmed raw array/CV colour reference is `91_array_rgb_confirmed_correct`
- GPIO motor adapter starts as `rpigpio`
- safe invalid-JSON API handling returns `PISD-API-001` instead of crashing
- live API camera start/frame/status/stop endpoints work
- one-by-one motor calibration testing is available for cars with different motor wiring
- standard validation prints simple `OK` / `FAIL` lines with `PISD-*` codes

Real wheel direction is intentionally left configurable for the later GUI settings page. Use the lifted-wheel motor channel tests to confirm each car's wiring before driving on the floor.

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
│   │   ├── templates/testing_server.html
│   │   └── static/               # testing GUI CSS/JS
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
│   └── TESTING_SERVER_GUI.md
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
    └── PATCH_NOTES_PiSD_0_2_1.md
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

The GUI files are:

```text
PiSD/pisd/web/templates/testing_server.html
PiSD/pisd/web/static/css/testing_server.css
PiSD/pisd/web/static/js/testing_server.js
```

Real motor output remains locked unless the page sends `enable_motor_output: true`; keep wheels lifted.

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


Standard all-in-one validation checklist. This prints simple `OK` / `FAIL` lines with PiSD codes and writes `test_outputs/standard_validation/summary.json`:

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

This saves comparison files under `test_outputs/camera_color/`. The first image, `01_request_awb_auto.jpg`, is the preferred preview baseline. When array diagnostics are enabled, `91_array_rgb` is the known-good raw array reference.

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
