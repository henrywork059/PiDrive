# PATCH NOTES — PiServer_0_1_21

## Goal
Restore camera preview colour behaviour closer to 0_1_15 / 0_1_16 and make Apply + Restart camera reconnect the preview immediately on the Camera tab.

## Changed files
- PiServer/piserver/services/camera_service.py
- PiServer/piserver/web/static/app.js
- PiServer/piserver/app.py

## Changes
1. Disabled the later automatic per-channel colour gain correction in `camera_service.py`.
   - Preview now stays on the raw colour path, matching the older working behaviour more closely.
2. Improved Camera tab preview restart flow in `app.js`.
   - After Apply + Restart camera, the current preview is cleared and the preview fetch loop is forced to reconnect twice.
3. Bumped app asset version to `0_1_21` in `app.py` so the browser reloads the updated JavaScript.

## Expected result
- Blue objects should no longer shift toward orange because of the later gain-correction layer.
- Camera preview should restart on the same tab after Apply + Restart camera without needing a tab switch.
