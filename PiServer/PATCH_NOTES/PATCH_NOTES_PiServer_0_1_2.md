# PATCH NOTES — PiServer 0_1_2

## Goal
Add a dedicated Calibration tab so the user can tune the car from the web UI without editing code, while keeping the selected drive mode and always-on server structure from 0_1_1.

## User request addressed
- Add one more tab for user to calibrate the car
- Allow setting the basis of each motor
- Allow setting max speed
- Allow setting turning ratio
- Allow setting camera resolution and related camera setup values

## Root cause / gap in 0_1_1
Version 0_1_1 introduced mode tabs and per-mode settings, but it still mixed together:
- drive-mode tuning
- low-level car calibration
- camera setup

There was no dedicated page for chassis and camera calibration, and no backend runtime path to apply those calibration changes live.

## Changes made

### 1) Added a dedicated top-level Calibration tab
Updated the web GUI top bar to include:
- Manual
- Lane Detection
- Full Auto
- Calibration

The new Calibration page has its own saved dock layout, just like the other pages.

### 2) Separated drive mode from selected UI page
Refactored runtime state so the backend now tracks:
- `drive_mode` = current active driving behavior
- `current_page` = currently selected UI tab

This means the Calibration page can stay open while the active drive mode remains Manual, Lane Detection, or Full Auto.

### 3) Added runtime calibration storage
Introduced a new persistent `calibration` section in `config/runtime.json` with:
- `left_motor_scale`
- `right_motor_scale`
- `global_speed_limit`
- `turn_gain`
- `camera_width`
- `camera_height`
- `camera_fps`
- `camera_format`

These values now save and reload with the runtime config.

### 4) Motor calibration support
Updated `MotorService` to support live calibration for:
- left motor trim
- right motor trim
- global speed cap
- turning ratio multiplier

The wheel output mapping now uses these values before sending PWM output.

### 5) Camera calibration support
Updated `CameraService` so the web UI can reapply:
- camera resolution
- target FPS
- camera pixel format

When these settings are changed, the camera backend is reopened using the new values.

### 6) Backend calibration API
Added a new endpoint:
- `POST /api/calibration/update`

This applies calibration immediately and updates runtime state without requiring code edits.

### 7) Calibration UI panel
Added a calibration workspace in the dock panel UI with controls for:
- Left motor trim
- Right motor trim
- Global max speed
- Turning ratio
- Camera resolution preset
- Camera FPS
- Camera format

The page includes an **Apply calibration** button and a **Load current values** button.

### 8) Documentation update
Updated `README.md` to document:
- the Calibration tab
- the new runtime calibration layer
- how calibration differs from per-mode tuning
- camera reopen behavior after changing camera settings

## Files changed
- `PiServer/config/runtime.json`
- `PiServer/README.md`
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`

## Verification performed
- Python syntax compilation completed for all project `.py` files
- JavaScript file passed syntax check with Node `--check`
- Zip rebuilt with updated `PiServer/` project and `PATCH_NOTES/`

## Notes / limitations
- Camera format support still depends on the backend available on the Pi hardware and software stack.
- Applying camera changes reopens the camera backend, so it should be done while the car is stationary.
- Full live code editing from the browser is still not implemented; this patch focuses on runtime calibration and configuration.

## Suggested next improvements
- Add a simple motor calibration wizard with step-by-step test buttons
- Add camera preview overlays for crop / center / horizon checking
- Add saveable calibration presets per chassis or battery profile
- Add recording of calibration values into session metadata
