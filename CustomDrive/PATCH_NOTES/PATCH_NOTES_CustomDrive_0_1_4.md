# PATCH NOTES — CustomDrive 0_1_4

## Goal
Align the new competition-side manual controller more closely with the existing PiServer structure and add a separate CustomDrive manual-control launcher for user-driven competition sessions.

## What was wrong / missing
1. **CustomDrive only had autonomous monitor launchers** (`run_custom_drive_gui.py`, `run_custom_drive_headless.py`). There was no dedicated PiServer-style manual driving console for competition rounds.
2. **Management style was split**. Some CustomDrive config/path logic was local-only, while the real live motor/camera stack lives under `PiServer/`. That made field debugging and maintenance harder.
3. **Config saves were not atomic** in the main CustomDrive settings helpers. A power loss or interrupted write could leave JSON partially written.
4. There was no clear place to save **competition session metadata** for the two manual-driving sessions.

## Final changes

### 1) Added a new PiServer-style manual control app
New files:
- `CustomDrive/run_custom_drive_manual.py`
- `CustomDrive/custom_drive/manual_control_app.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/manual_web/templates/index.html`
- `CustomDrive/custom_drive/manual_web/static/app.js`
- `CustomDrive/custom_drive/manual_web/static/styles.css`
- `CustomDrive/config/manual_control.json`

What it does:
- boots PiServer `CameraService`, `MotorService`, `ControlService`, `ModelService`, and `RecorderService`
- uses PiServer `runtime.json` for camera + motor runtime settings
- forces the `manual` algorithm so throttle/steering go through the real PiServer motor path
- exposes a browser manual-control UI with:
  - live camera preview
  - joystick + keyboard control
  - steer-mix and speed control
  - record toggle
  - e-stop / clear e-stop
  - save / reload runtime config
  - two built-in competition session slots (`session_1`, `session_2`)

### 2) Added shared path helpers
New file:
- `CustomDrive/custom_drive/project_paths.py`

This centralises repo/root/config paths and PiServer import bootstrapping so both CustomDrive live runtime and the new manual app use the same path logic.

### 3) Hardened JSON writes
Updated files:
- `CustomDrive/custom_drive/run_settings.py`
- `CustomDrive/custom_drive/runtime_settings.py`

Changes:
- moved config roots to the shared path helper
- switched saves to **atomic write + replace** instead of direct overwrite
- kept existing validation/clamping behavior

### 4) Made live runtime use shared PiServer path bootstrapping
Updated file:
- `CustomDrive/custom_drive/live_runtime.py`

This now uses the shared project path helper instead of duplicating its own PiServer import-path setup.

### 5) Updated documentation
Updated file:
- `CustomDrive/README.md`

Added:
- new `run_custom_drive_manual.py` launcher
- `manual_control.json`
- explanation of the new manual control app and how it differs from the autonomous GUI/headless launchers

## Why this is easier to manage now
- the new manual controller uses the **same core PiServer service objects** you already maintain
- camera/motor tuning still lives in **PiServer/config/runtime.json**
- competition-only metadata lives in **CustomDrive/config/manual_control.json** instead of being mixed into PiServer runtime state
- path handling is less duplicated
- config writes are safer

## Verification performed
1. `python -m compileall CustomDrive`
   - passed
2. Manual-control server files compile successfully with the rest of CustomDrive.
3. Settings helpers compile and normalise correctly.

## Limitations / notes
1. I could **not fully launch the Flask app inside this container** because `flask` is not installed here. The code compiles, but full browser runtime still needs your Pi environment.
2. The manual-control app is designed to use the **real PiServer motor path** only when `RPi.GPIO` is available on the Pi.
3. The manual app listens on **port 5060** by default so it does not clash with:
   - PiServer default web app (`5000`)
   - CustomDrive autonomous GUI (`5050`)

## Suggested run command on the Pi
```bash
cd ~/PiDrive/CustomDrive
python -m pip install -r requirements.txt
python run_custom_drive_manual.py
```

Then open:
```text
http://<pi-ip>:5060
```
