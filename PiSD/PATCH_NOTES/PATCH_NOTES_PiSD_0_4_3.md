# PiSD 0.4.3 Patch Notes

## Request summary
Verify the Main Dashboard Start / Live / Stop / Refresh button meanings do not conflict, and refine the preview overlay so it draws the intended path from the current throttle and steering values.

## Cause / reason for change
The previous overlay showed a rotated arc, which gave a general movement hint but did not clearly draw a path based on the actual throttle and steering values. The preview controls also used short labels such as `Start camera`, `Live preview`, and `Refresh`, which could be confused with motor STOP or status refresh actions.

## Files changed
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/css/main_dashboard.css`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_3.md`

## Behaviour changed
- Dashboard version updated to `0.4.3`.
- Renamed/clarified dashboard controls:
  - Top bar `Refresh` is now `Refresh status` and only refreshes status values.
  - `Start camera` is now `Start camera + live` and starts the camera service before switching to the live stream.
  - `Stop camera` is now `Stop camera only` and is explicitly camera-only, not a motor stop.
  - `Live preview` is now `Show live stream` and only reloads/switches the preview image to MJPEG live stream mode.
  - Red `STOP` buttons remain the motor stop/safety-stop controls.
- Added clearer title/help text so users can distinguish camera-preview actions from motor-output actions.
- Replaced the old CSS rotated arc with an SVG quadratic path drawn from throttle and steering.
- The intended path now changes with:
  - throttle magnitude: longer/thicker path when throttle is higher
  - throttle sign: forward path draws upward; reverse path draws downward with a dashed line
  - steering sign/magnitude: path curves left or right according to the steering value
- Removed a duplicate status refresh call after starting the camera.

## Compatibility notes
- No backend route or API contract was changed.
- Existing overlay toggle remains `mdOverlayToggle` and still defaults to on.
- Existing 0.4.1 cleanup/commented-out code and 0.4.2 overlay toggle behaviour were preserved.
- The patch is still client-side visualisation only; it does not draw onto saved frames or MJPEG bytes.

## Verification actually performed
- Ran `python -m compileall pisd scripts` from the PiSD folder.
- Ran `python scripts/test_main_dashboard.py --static-only`.
- Ran `python scripts/test_front_page_tabs.py --static-only`.
- Ran `python scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`.

## Known limits / next steps
- The path is a visual aid based on current/last intended throttle and steering values, not a calibrated physical vehicle trajectory model.
- A future patch can add overlay settings for opacity, line thickness, or camera-relative calibration once real driving tests confirm the preferred visual style.
