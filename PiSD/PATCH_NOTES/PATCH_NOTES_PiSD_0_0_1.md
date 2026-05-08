# PATCH NOTES — PiSD_0_0_1

## Request summary

Update the new `PiDrive/PiSD` sandbox so it is no longer only a placeholder. The user requested:

- keep only one dependency file, not both `requirements.txt` and `requirement.txt`
- add notes/instructions for folders, files, and directories
- patch in real camera service and motor service
- refer to the existing PiServer code and online references

## Cause / reason

`PiSD_0_0_0` was intentionally a minimal placeholder. It had duplicate dependency files and no real service layer. To begin rebuilding PiServer GUI/function behavior from square one, PiSD now needs real service boundaries for camera and motor control while still remaining safe to test on a PC.

## Files removed

```text
PiSD/requirement.txt
```

## Files added

```text
PiSD/config/defaults.json
PiSD/pisd/__init__.py
PiSD/pisd/app.py
PiSD/pisd/core/__init__.py
PiSD/pisd/core/value_utils.py
PiSD/pisd/services/camera_service.py
PiSD/pisd/services/motor_service.py
PiSD/docs/DIRECTORY_GUIDE.md
PiSD/docs/HARDWARE_SERVICES.md
PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_1.md
```

## Files changed

```text
PiSD/PiSD.py
PiSD/README.md
PiSD/requirements.txt
PiSD/docs/ARCHITECTURE.md
PiSD/docs/DEVELOPMENT_PLAN.md
PiSD/docs/GUI_FUNCTION_SPEC.md
PiSD/docs/TEST_PLAN.md
```

## Behavior changed

- `requirements.txt` is now the only dependency file.
- `PiSD.py` now launches the PiSD app package instead of containing all logic inline.
- Added `--hardware` flag for explicit real Raspberry Pi adapter mode.
- Default mode remains safe simulation.
- Added camera service with:
  - Picamera2 path when hardware mode is enabled and Picamera2 is available
  - simulated changing frame fallback
  - JPEG frame endpoint
  - MJPEG stream endpoint
- Added motor service with:
  - PiServer-style differential-drive mapping
  - RPi.GPIO-style PWM path when hardware mode is enabled and GPIO is available
  - simulation fallback and visible motor output logs
  - stop command path
- Added temporary web GUI controls for camera preview, manual steering/throttle, emergency stop, and status.

## New endpoints

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

## PiServer reference used

Reviewed these existing PiServer files from the uploaded repo:

```text
PiServer/piserver/services/camera_service.py
PiServer/piserver/services/motor_service.py
PiServer/piserver/app.py
```

The PiSD services reuse the same general ideas but do not import or overwrite PiServer code.

## Verification actually performed

Performed locally in this workspace:

- Confirmed `PiSD/requirement.txt` was removed.
- Confirmed only `PiSD/requirements.txt` remains as the dependency file.
- Ran `python3 -m py_compile` on `PiSD.py` and the new PiSD package modules.
- Ran `python3 PiSD.py --status-only` successfully.
- Ran direct service smoke checks for:
  - camera simulation start and frame creation
  - motor simulation manual update
  - motor stop output reset
- Confirmed the final zip contains only the `PiSD/` folder.

## Known limits / next steps

- Real camera and real GPIO behavior cannot be verified in this workspace because no Raspberry Pi camera/GPIO hardware is attached.
- No persistent runtime settings store has been added yet.
- No snapshot folder manager has been added yet.
- The web page is still a temporary service test shell, not the final GUI.
- Next recommended patch: add persistent settings, split the web UI into static/template files, and add snapshot/save-frame behavior.
