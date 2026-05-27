# PATCH NOTES - PiSD_0_8_4

## Request summary

User requested a follow-up patch after `PiSD_0_8_3` to:

1. Remove the Manual Drive `Steer strength` control because steering X should be direct.
2. Move the Motor Tuning `Back to Front Page` link because it was in the wrong place.
3. Reduce the Motor Tuning live preview size because the live camera overlay panel was too large.

This patch builds forward from `PiSD_0_8_0` plus accepted patches `PiSD_0_8_1_patch.zip`, `PiSD_0_8_2_patch.zip`, and `PiSD_0_8_3_patch.zip`.

## Cause / root cause

Manual Drive still had an extra page-level `steer_strength` slider left over from the older steering model. After `0_8_2`, the motor algorithm already uses linear steering X:

```text
turn_mag = abs(steering)
```

Keeping a Manual Drive steer-strength multiplier would make user-recorded labels less direct than AI-predicted labels, because the drag-pad X value would be scaled before reaching the motor command. That conflicts with the current clean training model where user X, recorded steering label, and AI steering output should mean the same thing.

The Motor Tuning page also kept its back link inside the title block instead of the header action/status area used by the other PiSD pages. The live preview height inherited a large calibration-panel size, which made the page harder to use because the camera overlay occupied too much vertical space.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/css/motor_tuning.css`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/SETTINGS_MANAGER.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_4.md`

## Exact behaviour changed

### Manual Drive steering is now direct

- Removed the Manual Drive `Steer strength` slider from the drag-pad panel.
- Manual Drive now sends steering directly from the drag-pad X coordinate:

```text
steering = x
```

- The steering readout now shows the direct X value.
- Changing speed still scales throttle only.
- The speed slider remains available.
- Legacy browser storage now stores only manual speed, not steer strength.

### Settings no longer exposes steer strength

- Removed `Steer strength` from the Settings page Manual Drive defaults form.
- Settings normalisation removes legacy `manual_drive.steer_strength` if it exists in an older runtime settings file.
- Legacy `steer_strength` values are ignored for compatibility rather than causing startup or settings-load errors.

### Motor Tuning back link moved

- Moved `Back to Front Page` into the Motor Tuning header action/status area.
- This matches the layout pattern used by the other PiSD pages, where navigation sits with status/action controls instead of inside the title text block.

### Motor Tuning live preview made smaller

- Reduced the live camera overlay preview height cap.
- New preview sizing uses:

```text
min-height: clamp(180px, 30vh, 360px)
max-height: min(46vh, 430px)
```

- Mobile fallback minimum was reduced from `300px` to `200px`.
- The preview still keeps the live camera frame under the SVG overlay for visual matching.

## Preserved behaviour / rollback check

Reviewed the latest accepted PiSD patch line before finalising:

- `0_8_1`: removed `turn_gain`, separated overlay tuning, added live camera-backed Motor Tuning overlay, and aligned Motor Tuning styling.
- `0_8_2`: removed motor `turn_curve`; steering X became linear.
- `0_8_3`: separated intended vehicle-motion output from hardware-signed motor output.

Confirmed this patch does not roll back:

- `turn_gain` removal.
- `turn_curve` removal from real motor steering.
- Linear X-to-turn motor mapping.
- Live camera-backed Motor Tuning overlay preview.
- Visual-only/manual overlay calibration.
- Intended output readouts for Manual Drive, Motor Tuning, AI Mode, and recordings.
- Existing speed, overlay, recording, camera, motor direction, max-speed, bias, `min_inside_speed`, `allow_pivot_turn`, and `arcade_mix` fallback behaviour.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/settings_tab.js
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/overlay_geometry.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_motor_steering_modes.py
node scripts/test_overlay_turn_rate_geometry.js
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Manual Drive source contract passes with no `Steer strength` slider or `mdrvSteer` control.
- Settings page source contract passes with no `steer_strength` input.
- Settings manager ignores and removes legacy `manual_drive.steer_strength`.
- Motor Tuning source contract confirms `Back to Front Page` is in the header action/status area.
- Motor Tuning source contract confirms the live preview has the compact height cap.
- Steering tests still confirm full/half/straight linear turn-rate behaviour and intended-output reporting.
- Standard validation passed in static/simulation mode.
- `PiSD.py --status-only` reports version `0.8.4`.

## Verification not performed / known limits

- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask browser-route tests were not run because the local container environment does not include Flask.

## Suggested Pi-side test sequence

1. Apply `PiSD_0_8_4_patch.zip` after `0_8_1`, `0_8_2`, and `0_8_3`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/manual-drive` and confirm:
   - only the `Speed` slider remains in the drag-pad panel;
   - dragging halfway right shows steering about `+0.50`;
   - dragging fully right shows steering about `+1.00`.
4. Open `/settings` and confirm Manual Drive defaults no longer include `Steer strength`.
5. Open `/motor-tuning` and confirm:
   - `Back to Front Page` is in the header/status action row;
   - the live camera preview is smaller and easier to use;
   - the overlay still draws over the camera frame.
