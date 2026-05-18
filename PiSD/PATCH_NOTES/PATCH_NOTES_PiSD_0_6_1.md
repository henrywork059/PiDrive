# PiSD 0.6.1 Patch Notes

## Request summary
Improve the Manual Drive / AI Mode visualised-path overlay because the current two-line guide does not read clearly as the path the car could take.

## Cause / root cause
The v6 overlay kept the accepted road-edge concept, corrected turn direction, strong curvature, no reverse drawing, and thin default line style, but it was still rendered mostly as two independent cubic SVG strokes plus a centre arrow. Without a visible road surface/corridor, the overlay could look like decorative guide lines rather than an actual drivable path.

## Files changed
- `pisd/__init__.py`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/templates/ai_mode.html`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_1.md`

## Exact behaviour changed
- Manual Drive overlay now draws a filled translucent road corridor between the two road-edge lines.
- AI Mode overlay now uses the same filled sampled path corridor, so the AI safe-command preview visually matches Manual Drive.
- The road shape is generated from multiple perspective samples instead of one simple cubic path, making the bottom wide, the horizon narrow, and turns read more like a projected future route.
- The left/right edge lines are offset from the sampled centre path using local normals, so the inner and outer edges bend differently instead of looking like two unrelated strokes.
- The accepted v6 direction convention is preserved: negative/left steering still shifts the visible future path toward the right side of the camera frame, and positive/right steering shifts it toward the left side.
- Reverse-motion visualisation remains hidden.
- The car rectangle marker remains hidden.
- Default calibration values are not changed, so existing user overlay settings are preserved.

## Verification actually performed
- Reviewed latest patch notes `0_5_10`, `0_5_11`, `0_5_12`, and stable note `0_6_0` for rollback risk before editing.
- `python3 -m compileall -q pisd scripts PiSD.py`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Full Flask route/API tests were not run because Flask is not installed in this container.
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Visual camera-frame alignment was not checked on the physical car; this remains a UI/geometry improvement rather than a calibrated camera-projection model.

## Known limits / next steps
- The overlay is still a visual prediction guide based on steering/throttle, not a calibrated real-world projection from camera intrinsics.
- If real-car testing shows the corridor sits too high/low on the camera frame, the next small patch should tune `baseY`, `horizonY`, or the path width geometry.
