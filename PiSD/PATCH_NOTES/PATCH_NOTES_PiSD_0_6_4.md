# PiSD 0.6.4 Patch Notes

## Request summary
Fix the Manual Drive and AI Mode visualised-path overlay because hardware/UI testing showed the left/right turn direction was inverted after the v0.6.3 overlay geometry update.

## Cause / root cause
The v0.6.3 shared overlay helper preserved the earlier screen-convention inversion by using `visualSteering = -safeSteering`. That kept the previous accepted mathematical convention, but real use showed it made the overlay turn direction appear opposite to the current Manual Drive / AI steering controls. Because Manual Drive and AI Mode now share `overlay_geometry.js`, the wrong sign affected both pages consistently.

## Files changed
- `pisd/__init__.py`
- `pisd/web/static/js/overlay_geometry.js`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_4.md`

## Exact behaviour changed
- Flipped the visual steering sign in the shared overlay geometry helper from `-safeSteering` to `safeSteering`.
- Manual Drive overlay now bends left on screen for left/negative steering and right on screen for right/positive steering.
- AI Mode overlay inherits the same corrected direction because it uses the same shared geometry helper.
- Kept all v0.6.3 improvements: shared helper, 56 samples, midpoint/RK-lite integration, tangent-normal road-edge offsets, matched X/Y pseudo-perspective depth, smoothed filled corridor, gradient surface, hidden reverse guide, and hidden car rectangle.
- Updated `pisd.__version__` to `0.6.4`.
- No runtime config files were changed or reset.

## Verification actually performed
- Reviewed latest patch notes `0_6_3`, `0_6_2`, and `0_6_1` before editing for rollback risk.
- Applied `PiSD_0_6_1_patch.zip`, `PiSD_0_6_2_patch.zip`, and `PiSD_0_6_3_patch.zip` onto a clean `PiSD_0_6_0.zip` working tree before making this patch.
- `node --check pisd/web/static/js/overlay_geometry.js`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- Node numerical check of shared geometry:
  - steering `-0.65` ended left of centre on screen;
  - steering `0.00` remained centred;
  - steering `+0.65` ended right of centre on screen.
- `python3 -m compileall -q pisd scripts PiSD.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Full Flask route/API tests were not run because Flask is not installed in this container.
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Real camera calibration, lens distortion coefficients, and homography/IPM projection were not added or tested.

## Known limits / next steps
- This patch fixes the observed left/right overlay inversion only. It does not change camera projection calibration or the physical steering model.
- If hardware testing shows the corrected direction is now right but the corridor still drifts near the OV5647 frame edges, the next improvement should be real camera calibration/homography support rather than more sign or pseudo-projection tuning.
