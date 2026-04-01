# CustomDrive

CustomDrive provides mission-flow and manual-control applications built on shared runtime abstractions for simulated and live Pi operation.

## Current documented entry points

From `CustomDrive/`:

- Demo runtime: `python run_custom_drive_demo.py`
- GUI web control: `python run_custom_drive_gui.py`
- Manual web mode: `python run_custom_drive_manual.py`
- Mission 1 web mode: `python run_custom_drive_web.py`
- Headless runtime launcher: `python run_custom_drive_headless.py`

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Recommended Python: **3.11**.

Pi-only features depend on hardware/runtime libraries (camera/GPIO/TFLite). In non-Pi environments, fallback/sim behavior may be used depending on selected mode.

## Important configuration files

- `config/runtime_settings.json`
- `config/run_settings.json`
- `config/mission1_session.json`
- `config/manual_control.json`
- `config/servo_test.json`
- `config/dual_servo_test.json`

## Manual GUI web control

Run:

```bash
python run_custom_drive_gui.py
```

Typical URL:
- local: `http://127.0.0.1:5050`
- LAN: `http://<pi-ip>:5050`

Features include:
- camera preview
- drag-pad/drive controls
- Drive Settings and Style Settings overlays
- arm-control buttons using `config/manual_control.json`

## Mission 1 note

Mission-session UI version marker is defined in:
- `custom_drive/mission1_session_app.py`

When updating docs for Mission 1 behavior, verify this marker and parser behavior in `mission1_tflite_detector.py` to avoid stale release-note assumptions.

## Bug-prevention reference

Before modifying detection, overlay, or session UI behavior, read:
- `../BUG_PREVENTION_NOTES.md`
