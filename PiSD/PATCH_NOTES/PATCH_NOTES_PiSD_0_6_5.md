# PiSD 0.6.5 Patch Notes

## Request summary
Change the Manual Drive overlay calibration controls from slider bars to number inputs.

## Cause / root cause
The overlay calibration panel still used `type="range"` sliders for path length, curve strength, opacity, and path width. Sliders made quick experimentation easy, but they were less precise once the overlay tuning became more sensitive after the v0.6.1 to v0.6.4 path-geometry patches.

## Files changed
- `pisd/__init__.py`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/js/manual_drive.js`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_5.md`

## Exact behaviour changed
- Replaced the Manual Drive overlay calibration sliders with numeric input fields:
  - Path length
  - Curve strength
  - Opacity
  - Path width
- Preserved the same setting IDs and persisted config keys:
  - `path_length_scale`
  - `curve_strength`
  - `opacity`
  - `path_width_scale`
- Preserved the same min/max/step ranges, so existing validation and saved settings remain compatible.
- Updated the calibration grid CSS so the number inputs fit cleanly in the existing Manual Drive panel.
- Changed overlay calibration binding to commit on number-field `change`, with Enter also applying the typed value.
- Kept the v0.6.4 corrected overlay direction and all v0.6.3 shared overlay geometry behaviour unchanged.
- Updated `pisd.__version__` to `0.6.5`.
- No runtime config file was changed or reset.

## Verification actually performed
- Reviewed latest PiSD patch notes `0_6_4`, `0_6_3`, `0_6_2`, and `0_6_1` before editing for rollback risk.
- Confirmed this patch only changes the Manual Drive overlay calibration UI and does not modify shared overlay geometry.
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/overlay_geometry.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 -m compileall -q pisd scripts PiSD.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Full Flask route/API tests were not run because Flask is not installed in this container.
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Browser interaction was checked at source/static-test level only; physical touch-screen/keyboard behaviour should be confirmed on the target device.

## Known limits / next steps
- The number inputs still use the existing overlay calibration ranges. If real hardware tuning needs values outside those ranges, update the clamp ranges intentionally in a later patch.
- AI Mode still uses the shared overlay geometry but does not expose a separate calibration panel on its page.
