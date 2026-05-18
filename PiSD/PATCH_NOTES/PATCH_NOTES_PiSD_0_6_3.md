# PiSD 0.6.3 Patch Notes

## Request summary
Improve the Manual Drive and AI Mode visualised-path overlay again because the v0.6.2 turning path still did not look enough like a real drivable path during curves.

The user-provided notes for this patch highlighted two main risks:
- the drawing should use a better turn/path prediction and smoother sampling rather than a simple decorative curve;
- the screen projection should keep horizontal and vertical perspective behaviour mathematically consistent so the path does not warp when it moves away from the centre of the camera frame.

## Cause / root cause
The v0.6.2 patch already moved the overlay to a kinematic sampled path with tangent-normal road-edge offsets. However, the geometry was still duplicated in both frontend pages, the integration was still simple Euler-style, the surface fill used straight polygon edges while the boundaries used smoothed SVG paths, and the vertical screen placement used a different depth curve from the horizontal perspective scaling. That mismatch can look acceptable while driving straight, but becomes more obvious when the predicted path curves strongly toward the side of the image.

## Files changed
- `pisd/web/static/js/overlay_geometry.js`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/templates/ai_mode.html`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_3.md`

## Exact behaviour changed
- Added shared `PiSDOverlayGeometry` helper used by both Manual Drive and AI Mode, reducing duplicate overlay geometry code.
- Increased overlay sampling from 33 points to 56 points for smoother sharp turns.
- Replaced the previous Euler-style trajectory update with a midpoint / RK-lite integration step.
- Added a light curvature entry blend so the visible path enters turns more naturally instead of snapping into a rigid constant-radius arc immediately.
- Kept the kinematic bicycle-style curvature basis using wheelbase, steering angle, and curve-strength scaling.
- Kept the accepted screen convention: negative/left steering bends the visible path toward the right side of the camera frame, and positive/right steering bends it toward the left side.
- Kept road edges offset from the local tangent normal before screen projection.
- Stabilised tangent-normal calculation by using a wider neighbouring-point span.
- Updated projection so screen `x` and `y` are both based on the same hyperbolic depth denominator, reducing curve warping when the path moves toward the side of the image.
- Added slight width tapering on tight turns near the far end of the path to reduce distorted-looking corridor edges.
- Updated filled corridor generation so the surface polygon follows the same smoothed quadratic segments as the two road-edge paths instead of being filled with straight line joins.
- Made the road surface more visible using a bottom-to-horizon SVG gradient, so the overlay reads more as a drivable corridor/path and less as two separate guide strokes.
- Softened the centre trace opacity so the filled road corridor and two road edges are visually dominant.
- Reverse-motion visualisation remains hidden.
- The car rectangle marker remains hidden.
- Existing overlay calibration values and runtime config behaviour are preserved.

## Verification actually performed
- Reviewed latest patch notes `0_6_2`, `0_6_1`, and `0_6_0` before editing for rollback risk.
- Confirmed the patch builds forward from the current v0.6.2 overlay state rather than replacing it with older files.
- `node --check pisd/web/static/js/overlay_geometry.js`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 -m compileall -q pisd scripts PiSD.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`
- Numerically checked representative steering samples with the shared overlay helper: left steering ends to the right side of the screen, right steering ends to the left side of the screen, and straight remains centred.

## Verification not performed
- Full Flask route/API tests were not run because Flask is not installed in this container.
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Real camera calibration, lens distortion coefficients, and a physical homography/IPM projection were not added or tested. This is still a browser-side visual prediction overlay, not a calibrated camera model.

## Known limits / next steps
- If hardware testing still shows the path drifting near the OV5647 frame edges, the next step should be real camera calibration/homography support instead of more pseudo-projection tuning.
- The shared helper centralises geometry, but it is still loaded by Manual Drive and AI Mode templates separately; future frontend bundling could make this more formal.
- Exact wheelbase/camera-forward offset values are still visual tuning constants and may need adjustment against real footage.
