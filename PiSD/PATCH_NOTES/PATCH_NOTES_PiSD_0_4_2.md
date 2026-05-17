# PiSD 0.4.2 Patch Notes

## Request summary
Add a preview-frame overlay that helps the user understand the current intended car movement from throttle and steering, with a dashboard button to turn the overlay on and off.

## Cause / reason for change
The live camera preview showed the scene only. It did not visually explain what the latest manual-drive command meant, so the user had to infer movement from button labels or raw status JSON.

## Files changed
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/css/main_dashboard.css`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_2.md`

## Behaviour changed
- Added a live drive overlay inside the dashboard camera preview frame.
- Added an `Overlay on/off` toggle button beside the camera preview controls.
- Overlay now visualises:
  - throttle value
  - steering value
  - forward/reverse/turn mode text
  - predicted direction/path indicator
  - left and right motor output values when returned by the motor service
- Overlay updates immediately when a manual drive button is pressed, then updates again from the API response/status payload.
- STOP commands immediately reset the overlay to stopped/zero output.

## Compatibility notes
- No backend API contract was changed.
- The overlay uses existing `/api/status`, `/api/control/manual`, and `/api/control/stop` motor status data.
- Camera stream and motor command paths are unchanged.
- Existing PiSD 0.4.1 cleanup/commented-out code was preserved.

## Verification actually performed
- Ran `python -m compileall pisd scripts` from the PiSD folder.
- Ran `python scripts/test_main_dashboard.py --static-only`.
- Attempted `python scripts/test_main_dashboard.py`; route-level Flask checks could not run in this container because Flask is not installed here. Static dashboard validation passed.
- Ran `python scripts/test_front_page_tabs.py --static-only`.
- Ran `python scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`.

## Known limits / next steps
- The overlay is a client-side visual aid. It does not draw onto the JPEG/MJPEG camera frame itself and is not stored in recorded images.
- It currently follows the last manual/status motor command, not a future autonomous path planner.
- A later patch can add user settings for overlay size, opacity, and colour if needed.
