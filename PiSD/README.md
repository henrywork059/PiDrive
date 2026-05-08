# PiSD

PiSD is a clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder. PiSD may refer to PiServer code for behavior patterns, but PiServer files must not be overwritten by PiSD experiments.

## Current version

`PiSD_0_0_1`

This patch keeps only one dependency file:

```text
PiSD/requirements.txt
```

`requirement.txt` was removed to avoid duplicate install instructions.

## Folder layout

```text
PiSD/
├── PiSD.py                       # main launcher
├── README.md                     # install/run overview
├── requirements.txt              # single pip dependency file
├── config/
│   └── defaults.json             # safe default camera/motor settings
├── pisd/
│   ├── __init__.py
│   ├── app.py                    # Flask GUI/API wiring
│   ├── core/
│   │   └── value_utils.py        # clamp/parse helpers
│   └── services/
│       ├── camera_service.py     # Picamera2 + simulation camera service
│       └── motor_service.py      # RPi.GPIO-style + simulation motor service
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── DIRECTORY_GUIDE.md
│   ├── GUI_FUNCTION_SPEC.md
│   ├── HARDWARE_SERVICES.md
│   └── TEST_PLAN.md
└── PATCH_NOTES/
    ├── PATCH_NOTES_PiSD_0_0_0.md
    └── PATCH_NOTES_PiSD_0_0_1.md
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

## API endpoints added in this patch

```text
GET  /api/status
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

## Hardware service notes

Camera service:

- uses Picamera2 when `--hardware` is enabled and Picamera2 is available
- falls back to a simulated changing frame when Picamera2 is unavailable
- exposes current JPEG frames through `/api/camera/frame.jpg`
- exposes MJPEG stream through `/video_feed`

Motor service:

- follows the existing PiServer differential-drive mapping style
- defaults to PiServer-like BCM pins: left `(17, 27)`, right `(22, 23)`
- uses RPi.GPIO-style PWM when `--hardware` is enabled and GPIO is available
- otherwise logs simulated motor outputs
- always provides `/api/control/stop`

## Development rule

Keep PiSD as a clean test path. Do not replace `PiServer/` until PiSD has been tested enough and the user explicitly asks for merge/replacement.
