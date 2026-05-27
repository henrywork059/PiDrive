# PiSD 0.8.10 Patch Notes

## Request summary

This patch continues from `PiSD_0_8_9` and updates Manual Drive overlay calibration so the seven visual tuning variables are no longer capped by the earlier user-facing min/max limits where practical.

The requested change was:

- remove the min/max caps from the Manual visual tuning / Overlay calibration variables as much as possible.

## Cause / root cause

`PiSD_0_8_9` added practical bounds to the seven Manual Drive overlay controls. Those bounds kept the overlay from becoming visually extreme, but they also stopped calibration values outside the preset range from being entered, saved, or restored.

For real-car/camera matching, the overlay sometimes needs values outside the original conservative limits. The overlay is visual-only, so those calibration values should not be artificially capped like motor safety settings.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_10.md`

## Behaviour changed

### Overlay calibration inputs are no longer UI-capped

The Manual Drive overlay calibration number inputs no longer include the previous `min` and `max` attributes for:

- `turn_rate_visual_scale`
- `path_length_scale`
- `path_width_scale`
- `base_y`
- `horizon_y`
- `perspective_scale`
- `opacity`

The controls still keep their `step`, `value`, and `inputmode` settings so they remain convenient to edit.

### Frontend normalisation no longer clamps overlay values

`manual_drive.js` no longer uses the previous `OVERLAY_CONTROL_LIMITS` table or `boundedOverlayValue()` for the seven overlay calibration settings.

It now keeps any finite numeric value entered by the user and only falls back to the default if the value is not a valid finite number.

### Backend settings normalisation no longer clamps overlay values

`SettingsManager` no longer clamps the seven persisted overlay values to the old ranges. It also no longer forces `base_y` to stay below `horizon_y` by a fixed margin.

The backend still rejects non-finite values such as invalid text, NaN, or infinity by falling back to defaults. This is only to keep `runtime_settings.json` safe and parseable.

### Renderer safety remains internal

The overlay renderer still contains internal drawing safeguards so extreme calibration values do not directly affect motor output or AI labels. These internal drawing safeguards are not user-facing calibration caps.

## Preserved behaviour / rollback check

Reviewed the latest accepted PiSD patch line before finalising:

- `0_8_7`: Motor Tuning page reset/removal of all tuning panels.
- `0_8_8`: Manual Drive overlay reduced to seven visual-only controls.
- `0_8_9`: Manual visual tuning popup grouped into Shape / Camera alignment / Visibility.

Confirmed this patch does not roll back:

- Linear X steering.
- Removal of `turn_gain` from real motor steering.
- Removal of motor `turn_curve` from real motor steering.
- Manual Drive steer-strength removal.
- Intended motor output display.
- Motor start dead-zone kick backend/settings.
- Motor Tuning page reset from `0_8_7`.
- Manual Drive overlay seven-key persisted schema from `0_8_8`.
- Manual visual tuning grouped popup from `0_8_9`.
- Overlay tuning remains visual-only and does not change motor output or recorded steering/throttle labels.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_recording_service.py
node scripts/test_overlay_turn_rate_geometry.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Manual Drive static test confirms the overlay calibration still renders with the seven-control grouped popup.
- Manual Drive static test confirms the calibration controls are now treated as reduced uncapped controls.
- Settings persistence test confirms overlay values outside the old min/max ranges are saved instead of being clamped.
- Settings persistence test confirms invalid/non-numeric overlay values fall back safely to defaults.
- Recording service test confirms the reduced overlay metadata schema is still recorded.
- Overlay geometry test confirms visual overlay scaling remains separate from real motor steering.
- Motor steering test confirms linear X steering and intended-output behaviour remain active.
- Standard validation passed in static/simulation mode.
- `PiSD.py --status-only` reports version `0.8.10`.

## Verification not performed / known limits

- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask browser-route tests were not run because this container environment does not include Flask.
- Extreme overlay values may make the road guide visually odd or off-screen, but they remain visual-only and can be reset with `Reset 7 defaults`.

## Suggested Pi-side test sequence

1. Apply this patch after `PiSD_0_8_9_patch.zip`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/manual-drive`.
4. Start the live camera stream.
5. Click `Manual visual tuning`.
6. Enter values outside the old limits, for example:
   - `Path length` above `2.5`
   - `Path width` above `1.2`
   - `Near Y` above `115`
   - `Horizon Y` below `5`
7. Apply visual calibration and confirm the page accepts the values.
8. Refresh/restart PiSD and confirm the values are still saved.
9. If the overlay becomes unusable, click `Reset 7 defaults`.
