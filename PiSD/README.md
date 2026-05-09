# PiSD

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behavior patterns, but PiServer files must not be overwritten by PiSD experiments.

## Current version

`PiSD_0_0_4`

This version keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` must not be restored.

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
│   └── TEST_PLAN.md
└── PATCH_NOTES/
    ├── PATCH_NOTES_PiSD_0_0_0.md
    ├── PATCH_NOTES_PiSD_0_0_1.md
    ├── PATCH_NOTES_PiSD_0_0_2.md
    ├── PATCH_NOTES_PiSD_0_0_3.md
    └── PATCH_NOTES_PiSD_0_0_4.md
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

This saves comparison files under `test_outputs/camera_color/`. The first image, `01_request_awb_auto.jpg`, is the new preferred preview baseline.

Raw array colour-order checks:

```bash
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb --output test_outputs/array_rgb.jpg
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order bgr --output test_outputs/array_bgr.jpg
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
