# PiSD 0.9.2 Patch Notes — Keyboard steering ramp timing to 0.8 s

## Request summary

The user asked to change the Manual Drive keyboard steering timing from `0.5 s` to `0.8 s`.

This applies to both sides of the keyboard steering behaviour:

- holding `Arrow Left` / `Arrow Right` ramps steering from centre to full left/right over `0.8 s`;
- releasing the left/right arrow key returns steering back to centre over `0.8 s`.

## Cause / reason

`PiSD_0_9_0` introduced keyboard driving with a `0.5 s` full-scale steering ramp. `PiSD_0_9_1` added return-to-centre on key release using the same `0.5 s` scale. The user wanted a slower, smoother steering change.

## Files changed

- `PiSD/pisd/__init__.py`
  - Bumped runtime/static asset version from `0.9.1` to `0.9.2`.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Changed `KEYBOARD_STEERING_FULL_SCALE_MS` from `500` to `800`.
  - Updated keyboard status text from `0.5 s` to `0.8 s`.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Updated the visible keyboard help text from `0.5 s` to `0.8 s`.
- `PiSD/scripts/test_manual_drive_page.py`
  - Updated static contract checks to expect the `0.8 s` keyboard text and the `800` ms constant.
- `PiSD/README.md`
  - Updated keyboard driving instructions.
- `PiSD/docs/MOTOR_CALIBRATION.md`
  - Updated keyboard calibration table.
- `PiSD/docs/STABLE_BASELINE.md`
  - Updated current keyboard-control description.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_2.md`
  - Added this note.

## Exact behaviour changed

Before:

```text
Hold Arrow Left/Right -> steering reaches -1/+1 in 0.5 s
Release Arrow Left/Right -> steering returns to 0 in 0.5 s
```

After:

```text
Hold Arrow Left/Right -> steering reaches -1/+1 in 0.8 s
Release Arrow Left/Right -> steering returns to 0 in 0.8 s
```

The throttle step remains unchanged:

```text
Arrow Up   -> throttle +0.05 per press
Arrow Down -> throttle -0.05 per press
Space      -> STOP and clear keyboard throttle/steering
```

## Compatibility notes

- Linear steering is preserved.
- Motor start dead-zone kick behaviour from `0.9.1` is preserved.
- Intended motor output display is preserved.
- Overlay tuning remains visual-only and does not affect motor steering or AI labels.
- The patch bumps the app version to `0.9.2`, so versioned static assets should reload after a browser hard refresh.

## Verification performed

Performed locally after applying this patch over `PiSD_0_9_0 + PiSD_0_9_1_patch`:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

The checks passed in this local static/simulation environment.

## Not verified here

- Real keyboard driving on the Raspberry Pi browser.
- Physical motor response timing on the car.
- Hardware camera/motor operation.
