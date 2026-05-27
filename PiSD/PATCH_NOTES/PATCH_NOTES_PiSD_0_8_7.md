# PiSD 0.8.7 Patch Notes

## Request summary

This patch continues from `PiSD_0_8_6` and applies the requested Motor Tuning reset:

- Remove all panels from the Motor Tuning page.
- Keep only a clean page header, status/navigation row, and a rebuild placeholder.
- Prepare the page to be redesigned from scratch without rolling back accepted backend motor behaviour.

## Cause / root cause

The Motor Tuning page had grown through several rapid calibration patches. It contained safety arming, timed motion tests, live camera preview, overlay controls, motor settings, and logging panels in one page. The latest screenshot and follow-up instruction showed the page layout had become too crowded and should be cleared so the tuning workflow can be rebuilt deliberately.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/css/motor_tuning.css`
- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/pisd/web/static/js/motor_tuning.js`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/README.md`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_7.md`

## Behaviour changed

### Motor Tuning page is cleared

The `/motor-tuning` page no longer renders the previous panels:

- Safety arming panel removed.
- Timed straight/turn/custom motion panel removed.
- Live camera + overlay preview panel removed.
- Motor settings panel removed.
- Overlay calibration panel removed.
- Log panel removed.

The page now contains only:

- page title/header,
- `Back to Front Page` navigation,
- current status code/version/motor adapter readout,
- a rebuild placeholder explaining that the panels were intentionally removed.

### Old Motor Tuning JavaScript disabled

`motor_tuning.js` is now a minimal reset-page helper. It only reads the initial status JSON and updates the header status/adapter text if available. It no longer binds old tuning buttons, camera controls, overlay drawing, timed test forms, or settings forms.

### Shared layout override reset

The Motor Tuning-specific shared layout rules in `pisd_layout_system.css` no longer assign grid areas for removed panels. The page is now a single-column rebuild workspace.

### Front page and documentation updated

The front-page Motor Tuning card and README/Motor Calibration notes now describe `/motor-tuning` as a cleared rebuild workspace instead of a working timed-test and overlay-calibration page.

## Preserved behaviour / rollback check

Reviewed the latest accepted PiSD patch line before finalising:

- `0_8_4`: Manual Drive steer-strength removal, Motor Tuning back-link placement, compact preview sizing.
- `0_8_5`: motor start dead-zone kick, two-column Motor Tuning attempt, Manual-Drive-style Motor Tuning overlay.
- `0_8_6`: final shared-CSS fix for equal-width Motor Tuning columns.

Because the user explicitly requested removing all Motor Tuning panels, this patch intentionally removes the previous Motor Tuning UI panels from the rendered page. It does **not** roll back these accepted backend/runtime behaviours:

- Linear X steering remains active in `MotorService`.
- `turn_gain` remains removed from real motor steering.
- Motor `turn_curve` remains removed from real motor steering.
- Intended motor output remains separated from hardware-signed output.
- Manual Drive steer-strength remains removed.
- Motor start dead-zone kick settings and hardware-layer kick behaviour remain in the backend/settings schema.
- Overlay tuning remains separate from real motor output for the next design.
- `/api/motor/tune-run` remains available for a future rebuilt UI or direct API checks.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/motor_tuning.js
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Motor Tuning static test confirms the reset page contract.
- Old Motor Tuning panel/control IDs such as `mtunRunTurn`, `mtunCameraPreview`, `mtunApplyOverlay`, and `mtunSafetyAck` are no longer rendered.
- Shared layout CSS no longer references removed Motor Tuning panel grid areas.
- Motor steering tests still confirm linear X steering and intended-output behaviour.
- Settings persistence still confirms start dead-zone values and legacy steering cleanup behaviour.
- Standard validation passed in static/simulation mode.
- `PiSD.py --status-only` reports version `0.8.7`.

## Verification not performed / known limits

- Real Raspberry Pi browser rendering was not hardware-tested here.
- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask route tests were not run because this container environment does not include Flask.

## Suggested Pi-side test sequence

1. Apply this patch after `PiSD_0_8_6_patch.zip`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/motor-tuning`.
4. Confirm only the header/status row and rebuild placeholder remain.
5. Confirm old tuning panels, live camera overlay preview, timed run controls, motor settings controls, overlay controls, and log panel are gone.
6. Open `/manual-drive` and `/settings` to confirm the accepted motor algorithm/settings behaviour is still available outside the cleared Motor Tuning page.
