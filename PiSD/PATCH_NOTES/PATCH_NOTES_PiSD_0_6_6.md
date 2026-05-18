# PiSD 0.6.6 Patch Notes

## Request summary
Update the Manual Drive overlay settings because the v0.6.5 number fields still behaved like the old sliders: their values were constrained by the old min/max ranges, and the settings panel still lived in a compact drop-down area. The requested change was to release the numeric value clamps, make overlay settings a larger popup, and expose more overlay tuning values.

## Cause / root cause
The v0.6.5 UI changed the controls from sliders to number inputs, but it intentionally preserved the earlier slider ranges. The constraints remained in three places:

- the HTML number inputs still used old `min` / `max` attributes;
- the Manual Drive frontend `normaliseOverlaySettings()` still clamped overlay values to the old ranges;
- the backend `SettingsManager` still clamped persisted overlay values when loading/saving runtime settings.

That made the controls more precise than sliders, but not truly open for hardware tuning.

## Files changed
- `pisd/__init__.py`
- `pisd/core/settings_manager.py`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/overlay_geometry.js`
- `scripts/test_settings_persistence.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_6_6.md`

## Exact behaviour changed
- Replaced the compact Manual Drive overlay settings drop-down area with a larger popup dialog.
- Kept the overlay settings as number inputs, but removed the old overlay `min` / `max` attributes from those number fields.
- Released the Manual Drive frontend overlay setting normalisation so user-entered finite numbers are preserved instead of being forced back into the old slider ranges.
- Released backend persisted overlay setting normalisation in `SettingsManager` so saved overlay values are no longer clamped to the old v0.6.5 limits.
- Kept internal renderer safety guards where needed to prevent invalid SVG/performance problems. For example, opacity is still bounded when applied to CSS, and sample count/projection denominators have renderer-side safety limits. The user-entered setting values themselves are still preserved.
- Added more Manual Drive overlay tuning values:
  - `sample_count`
  - `wheelbase`
  - `max_steer_rad`
  - `curve_response`
  - `curvature_scale`
  - `curvature_limit`
  - `entry_blend_start`
  - `road_half_width`
  - `base_y`
  - `horizon_y`
  - `camera_forward_offset`
  - `near_clip`
  - `perspective_scale`
  - `perspective_depth`
  - `turn_compression`
  - `turn_width_taper`
- Updated the shared overlay geometry helper to use the new advanced settings while preserving the v0.6.4 corrected left/right steering direction and the v0.6.3 road-corridor rendering approach.
- Added popup controls for applying numbers, resetting overlay defaults, closing by button, closing by Escape, and closing by clicking the popup backdrop.
- Updated the settings persistence test so it now verifies unclamped overlay values are preserved.
- Updated `pisd.__version__` to `0.6.6`.

## Compatibility notes
- Existing runtime settings remain backward compatible. Missing new overlay keys are filled from defaults.
- Old saved overlay values still load normally.
- Non-numeric values fall back to defaults for that key.
- This patch does not change motor output, AI motor safety, recording format, camera defaults, or the accepted overlay left/right direction correction.

## Verification actually performed
- Reviewed latest PiSD patch notes `0_6_5`, `0_6_4`, and `0_6_3` before editing for rollback risk.
- Applied `PiSD_0_6_1_patch.zip` through `PiSD_0_6_5_patch.zip` onto a clean `PiSD_0_6_0.zip` working tree before making this patch.
- Confirmed the overlay inputs in `manual_drive.html` no longer contain old overlay `min` / `max` attributes.
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
- Real browser/touchscreen popup interaction was not tested on the target Pi display.

## Known limits / next steps
- The renderer still has local safety bounds for values that can break the SVG or browser performance, especially sample count, opacity rendering, projection depth, and screen coordinate clamping. This is intentional page safety, not persisted settings clamping.
- The advanced overlay settings are exposed in Manual Drive. AI Mode continues to use the shared overlay geometry helper with its defaults, but it does not yet have a separate advanced settings popup.
- Hardware tuning should start with `curve_strength`, `path_width_scale`, `base_y`, `horizon_y`, `perspective_scale`, `camera_forward_offset`, and `turn_width_taper` before changing deeper model values.
