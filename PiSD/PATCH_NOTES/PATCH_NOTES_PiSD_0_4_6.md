# PiSD_0_4_6 Patch Notes

## Request summary
- Improve the Manual Drive preview overlay after online research on how vehicle path visualisations are commonly drawn.
- The overlay should make throttle/steering movement clearer to the driver.
- Keep the existing Manual Drive overlay button and cumulative 0_4_1 through 0_4_5 fixes intact.

## Research basis
- Common car-like steering visualisations use a simplified bicycle/Ackermann style model: speed/throttle affects how far the vehicle is projected, while steering angle affects the curvature of the path.
- Smooth vehicle paths are often represented with straight-line and circular-arc segments, so this patch avoids a single hand-shaped quadratic curve and uses sampled constant-curvature points instead.

## Cause / issue
- The previous overlay used a single quadratic SVG curve. It showed general left/right intention, but it was not shaped like a car-style path prediction.
- Strong steering could look too artificial because the control point was manually scaled rather than sampled from a motion approximation.
- The overlay did not clearly identify path tightness or the predicted endpoint.

## Files changed
- `PiSD/pisd/__init__.py`
  - Bumped version from `0.4.5` to `0.4.6`.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Changed overlay HUD label from `Intended path` to `Predicted arc`.
  - Added curve/tightness readout: `mdrvOverlayCurveLabel`.
  - Added wider path glow path: `mdrvOverlayPathWide`.
  - Added white guide path: `mdrvOverlayPathGuide`.
  - Added start and endpoint markers: `mdrvOverlayStartPoint`, `mdrvOverlayEndpoint`.
  - Updated notice text to describe the overlay as a sampled predicted arc.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Replaced the simple quadratic path formula with sampled constant-curvature path generation.
  - Added `sampledIntendedPath()`, `pointsToPath()`, and `curveLabelText()` helpers.
  - Kept throttle as the visual horizon length control.
  - Kept steering as the curvature control.
  - Mirrored reverse visualisation so the user sees the backing direction more clearly.
  - Added endpoint marker updates.
  - Added `data-overlay-motion` state on the preview frame for forward/reverse/stopped styling.
- `PiSD/pisd/web/static/css/manual_drive.css`
  - Reworked the overlay styling for a clearer projected path.
  - Added wider underlay, guide stroke, endpoint marker, and reverse colour state.
  - Added subtle road/lane guide background inside the overlay.
  - Improved small-screen layout for the overlay HUD and wheel readout.
- `PiSD/scripts/test_manual_drive_page.py`
  - Updated static contract checks to require the new sampled predicted-arc elements and helpers.

## Behaviour changed
- Manual Drive overlay now draws a sampled arc rather than a single quadratic curve.
- Throttle magnitude lengthens/shortens the predicted path.
- Steering magnitude tightens/loosens the curve.
- Reverse path is dashed and highlighted separately.
- Endpoint marker shows where the current command is projected to go in the overlay view.
- The overlay remains visual only. It does not change motor output or control logic.

## Compatibility notes
- This is a cumulative patch over the 0_4_0 baseline plus the 0_4_1 to 0_4_5 patch line.
- Existing runtime settings are not reset.
- Existing camera, motor, recording, and Manual Drive API routes are not changed.

## Verification actually performed
- Applied the cumulative patch stack over a clean `PiSD_0_4_0` folder before editing.
- Ran `python3 -m compileall -q .` successfully.
- Ran `python3 scripts/test_manual_drive_page.py --static-only` successfully.
- Ran `python3 scripts/test_main_dashboard.py --static-only` successfully.
- Ran `python3 scripts/test_front_page_tabs.py --static-only` successfully.
- Ran `python3 scripts/test_ui_presentation_consistency.py --static-only` successfully.
- Ran `node --check pisd/web/static/js/manual_drive.js` successfully.
- Ran `python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor` successfully.

## Known limits / next steps
- The overlay is still an approximate visual aid, not calibrated to measured wheelbase, camera FOV, wheel slip, or exact motor response.
- Future improvement: add calibration settings for visual wheelbase / max steering angle / camera perspective once the car frame and camera mounting are final.
- Full Flask route validation could not be run in this container because Flask is not installed here.
