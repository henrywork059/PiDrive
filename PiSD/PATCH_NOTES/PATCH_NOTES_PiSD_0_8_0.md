# PiSD 0.8.0 Stable Package Notes

## Request summary

Package v8 as a full stable PiSD package after the accepted `0_7_1` through `0_7_3` patch line.

This package promotes the current accepted PiSD work into `PiSD_0_8_0.zip` and sets it up as the next stable rollback baseline.

## Built from

- Starting baseline: `PiSD_0_7_0.zip`
- Applied accepted patches:
  - `PiSD_0_7_1_patch.zip`
  - `PiSD_0_7_2_patch.zip`
  - `PiSD_0_7_3_patch.zip`

## Included accepted behaviour

### 0.7.1 steering algorithm

- Added the new `turn_rate` steering mode.
- Kept the old `arcade_mix` mode as a selectable fallback.
- In `turn_rate` mode:
  - left/right input controls curve tightness;
  - up/down input controls travel speed along that curve;
  - inside wheel slows down instead of immediately reversing;
  - pivot turning is disabled by default unless explicitly enabled.
- Added motor tuning values:
  - `steering_mode`
  - `turn_gain`
  - `turn_curve`
  - `min_inside_speed`
  - `allow_pivot_turn`

### 0.7.2 overlay calculation alignment

- Updated the visual road-path overlay to follow the new `turn_rate` steering meaning.
- The overlay curve now follows the same unitless turn-intent calculation used by motor output:

```text
turn_intent = sign(steering) * abs(steering) ** turn_curve * turn_gain
```

- Manual Drive and AI Mode now pass current motor steering settings into the shared overlay geometry.
- Added `turn_rate_visual_scale` so the visual path can be tuned independently after the real motor turn is correct.
- Kept `arcade_mix` overlay fallback support.

### 0.7.3 motor tuning and overlay-match workflow

- Added `/motor-tuning` page.
- Added timed straight, turn, and custom motor tuning runs.
- Added `POST /api/motor/tune-run`.
- Timed tune runs use the same `MotorService.update()` path as Manual Drive and AI Mode.
- Timed tune runs stop automatically in a `finally` path after the selected duration.
- Added motor tuning controls and overlay tuning controls on the same page so the user can match the drawn predicted path to the real car motion.

## Files changed for this stable package

- `pisd/__init__.py`
  - Promoted package version to `0.8.0`.
- `README.md`
  - Updated current version and install instructions for `PiSD_0_8_0.zip`.
  - Documented v8 as the current rollback baseline.
  - Updated future patch naming to `PiSD_0_8_x_patch.zip`.
- `docs/STABLE_BASELINE.md`
  - Promoted stable baseline to `PiSD_0_8_0`.
  - Added the accepted `0_7_1` through `0_7_3` steering, overlay, and motor-tuning work to the baseline summary.
  - Updated future patch naming to `0_8_x`.
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_8_0.md`
  - Added this stable package note.

All functional files from the accepted `0_7_1`, `0_7_2`, and `0_7_3` patch zips are included in the full package.

## Verification actually performed

Working tree was created by extracting clean `PiSD_0_7_0.zip`, then applying `0_7_1`, `0_7_2`, and `0_7_3` patch zips in order.

Performed checks:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/overlay_geometry.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/settings_tab.js
node scripts/test_overlay_turn_rate_geometry.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
```

Also manually ran a simulation-only timed-drive check using `MotorService.run_timed_drive()` to confirm a timed turn-rate command stops after the requested short duration.

## Verification limits

- Full Flask route checks were not completed in this packaging container because Flask is not installed here.
- `/motor-tuning` static source checks passed, and the timed-drive helper was checked in simulation mode, but the live Flask route was not exercised in this container.
- `scripts/test_front_page_tabs.py` confirmed its static file/source checks before failing at Flask app creation because Flask is not installed here.
- Raspberry Pi camera hardware was not tested in this container.
- Raspberry Pi motor hardware was not tested in this container.
- Browser/touchscreen interaction was not tested on real Pi hardware.

## Packaging notes

- This is a full stable package, not a patch-only zip.
- The package keeps the exact `PiSD/` top-level folder structure.
- Generated `__pycache__` folders and transient validation JSON outputs were removed before final zipping.
- `test_outputs/README.md` is retained; generated test result files are not bundled.

## Future patch rule

Future PiSD bug-fix patches after this package should build forward from `PiSD_0_8_0.zip` and use naming like:

```text
PiSD_0_8_1_patch.zip
PiSD_0_8_2_patch.zip
```

unless the user promotes another stable baseline.
