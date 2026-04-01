# PiDrive

PiDrive is a monorepo for Raspberry Pi car runtime, model training, and mission-control workflows.

This document is synchronized to the **current repository snapshot** (not historical patch lines).

## Repository status (current snapshot)

### Actively used projects
- `PiServer/` — modular Flask runtime and web dashboard for camera/motor/control/model operations
- `piTrainer/` — desktop trainer for driving models (steer/throttle)
- `CustomTrainer/` — desktop YOLO workflow (label, train, validate, export)
- `CustomDrive/` — mission and manual control utilities built around PiServer-style services
- `PiBooter/` — Pi startup/network helper app
- `piCar_0_3_2/` — legacy runtime retained for compatibility

### Reference/archive artifacts
- `PiServer_0_3_4/`, `PiServer_0_4_1/`
- timestamped `.zip` snapshots at repo root

## Runtime/version markers found in code

- `PiServer/piserver/app.py` -> `APP_VERSION = "0_4_10"`
- `PiServer/piserver/web/static/app.js` -> layout key namespace `v0_3_21`
- `CustomDrive/custom_drive/mission1_session_app.py` -> `APP_VERSION = '0_4_15'`
- `CustomTrainer/custom_trainer/ui/main_window.py` -> window title `CustomTrainer 0_2_11`

> If patch-note files mention newer numbers than the constants above, treat those patch notes as historical documentation unless matching code is present.

## Requirements matrix

| Project | Python | Install command |
|---|---|---|
| PiServer | 3.10+ (3.11 preferred) | `pip install -r PiServer/requirements.txt` |
| piTrainer | 3.10+ (3.11 preferred) | `pip install -r piTrainer/requirements.txt` |
| CustomTrainer | 3.10+ (3.11 preferred) | `pip install -r CustomTrainer/requirements.txt` |
| CustomDrive | 3.10+ (3.11 preferred) | `pip install -r CustomDrive/requirements.txt` |
| PiBooter | 3.10+ | `pip install -r PiBooter/requirements.txt` |

Pi-only optional runtime dependencies include `picamera2`, `RPi.GPIO`, and `tflite-runtime`.

## Standard setup pattern

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
```

Then install the specific project requirements file.

## Launch commands (canonical)

- PiServer: `python PiServer/server.py`
- piTrainer: `python piTrainer/main.py`
- CustomTrainer: `python CustomTrainer/run_custom_trainer.py`
- CustomDrive demo: `python CustomDrive/run_custom_drive_demo.py`
- CustomDrive GUI web: `python CustomDrive/run_custom_drive_gui.py`
- PiBooter: `python PiBooter/run_pibooter.py`

## Instructional docs index

- Repository maintenance/process: `INSTRUCTIONS.md`
- Cross-project bug prevention guidance: `BUG_PREVENTION_NOTES.md`
- PiServer usage: `PiServer/README.md`
- CustomTrainer workflow: `CustomTrainer/README.md`
- CustomDrive workflow: `CustomDrive/README.md`
- piTrainer docs: `piTrainer/README.md`
- Pi runtime helper for exported models: `CustomTrainer/custom_trainer/assets/pi_runtime/README_PI.md`

## Known doc-version caveat

Some `PATCH_NOTES/` files document attempted or forward patches that may not match this checkout exactly. Validate behavior against code constants and entry points before deploying.
