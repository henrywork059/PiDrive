# PATCH NOTES - PiSD_0_8_2

## Request summary

User clarified that drag-pad / AI steering X should linearly control the turning amount.

This patch builds forward from `PiSD_0_8_0` plus accepted `PiSD_0_8_1_patch.zip` and changes the current motor steering behaviour to:

```text
turn_mag = abs(steering)
```

It keeps overlay tuning separate from motor tuning. The overlay can still be manually matched to the real car motion using visual-only settings on the Motor Tuning page.

## Cause / root cause

`PiSD_0_8_1` correctly removed `turn_gain` from the motor algorithm, but it still kept motor `turn_curve` as a steering response shaper:

```text
turn_mag = abs(steering) ** turn_curve
```

That meant the maximum turning range was correct, but the middle of the X-axis was still non-linear. For example, with `turn_curve = 1.5`, `x = 0.5` produced about `0.35` turn magnitude rather than a direct half-tight turn.

The requested control model is simpler:

```text
x = 0.0  -> straight
x = 0.5  -> half-tight turn
x = 1.0  -> tightest non-pivot turn
```

Therefore `turn_curve` should no longer be a real motor steering value.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/config/defaults.json`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/js/motor_tuning.js`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/js/overlay_geometry.js`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/README.md`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/SETTINGS_MANAGER.md`
- `PiSD/scripts/test_motor_steering_modes.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/scripts/test_overlay_turn_rate_geometry.js`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_2.md`

## Exact behaviour changed

### Real motor steering is now linear in `turn_rate` mode

Removed motor `turn_curve` from the active `turn_rate` motor calculation.

Old `0_8_1` calculation:

```text
turn_mag = abs(steering) ** turn_curve
```

New `0_8_2` calculation:

```text
turn_mag = abs(steering)
```

With default `min_inside_speed = 0.0` and `allow_pivot_turn = false`:

```text
steering = 0.00, throttle = 0.40 -> left = 0.40, right = 0.40
steering = 0.50, throttle = 0.40 -> left = 0.40, right = 0.20  # right turn
steering = 1.00, throttle = 0.40 -> left = 0.40, right = 0.00  # tightest right turn
steering = -1.00, throttle = 0.40 -> left = 0.00, right = 0.40 # tightest left turn
```

### Motor `turn_curve` removed from UI and settings

Removed motor `Turn Curve` inputs from:

- Settings page
- Testing page
- Motor Tuning page

Runtime settings normalisation now removes both legacy keys:

```text
turn_gain
turn_curve
```

Existing saved `runtime_settings.json` files that contain either key are still safe. The keys are ignored and removed from normalised settings instead of breaking startup.

### Overlay tuning remains separate and manual

Overlay path drawing still uses visual-only settings such as:

- `turn_rate_visual_scale`
- `curve_response`
- `curve_strength`
- `curvature_scale`
- projection / width / taper controls

Those settings affect only the drawn overlay. They do not change motor output.

The Motor Tuning page keeps the live camera-backed overlay preview from `0_8_1`, so the user can manually match the overlay to the real car motion.

### Compatibility preserved

- `arcade_mix` fallback remains available.
- `steer_mix` remains available for `arcade_mix` only.
- `min_inside_speed` remains available for the non-pivot `turn_rate` inside-wheel floor.
- `allow_pivot_turn` remains available for explicit pivot behaviour.
- Existing camera, recording, AI Mode, overlay metadata, live preview, and Motor Tuning page styling changes from `0_8_1` are preserved.

## Rollback-risk review

Before finalising, reviewed the latest relevant PiSD patch history:

- `0_7_2`: overlay was aligned with the turn-rate steering model and overlay metadata preservation.
- `0_7_3`: Motor Tuning page, timed motor tests, and overlay match calibration were added.
- `0_8_0`: full stable v8 package promoted from accepted v7 patch line.
- `0_8_1`: `turn_gain` removed from motor steering; live camera-backed Motor Tuning overlay and style alignment added.

Confirmed this patch does not roll back:

- Motor Tuning page route and `/api/motor/tune-run` endpoint.
- Live camera frame under the Motor Tuning overlay.
- Separate overlay calibration controls.
- Visual-only overlay behaviour.
- `turn_gain` removal from real motor steering.
- Manual Drive / AI Mode shared overlay renderer.
- Recording and screenshot overlay metadata.
- AI Mode safety/session-only motor enable behaviour.
- `arcade_mix` fallback.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/overlay_geometry.js
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/settings_tab.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
node scripts/test_overlay_turn_rate_geometry.js
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Full right steering with throttle `0.40` produced left `0.40`, right `0.00` in simulation.
- Full left steering with throttle `0.40` produced left `0.00`, right `0.40` in simulation.
- Half right steering with throttle `0.40` produced left `0.40`, right `0.20` in simulation, confirming linear X-to-turn mapping.
- Straight steering still produced equal wheel outputs.
- Optional pivot mode still works when explicitly enabled.
- Settings persistence confirmed legacy `turn_gain` and `turn_curve` are ignored and not returned in normalised motor settings.
- Overlay geometry test confirmed visual overlay response remains controlled by overlay settings rather than motor tuning values.
- Status-only launch reports PiSD version `0.8.2`; motor status no longer includes `turn_gain` or `turn_curve`.

## Verification not performed / known limits

- Full Flask route tests were not run in this container because Flask is not installed here.
- Real Raspberry Pi camera preview was not hardware-tested in this environment.
- Real Raspberry Pi motor movement was not hardware-tested in this environment.

## Suggested Pi-side test sequence

1. Apply this patch after `PiSD_0_8_1_patch.zip`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/motor-tuning`.
4. Confirm the live camera frame appears under the overlay.
5. Lift the wheels or clear a safe area.
6. Run short timed tests:
   - straight: `steering = 0.00`
   - half right: `steering = 0.50`
   - full right: `steering = 1.00`
   - full left: `steering = -1.00`
7. Confirm half steering gives a visibly wider turn than full steering.
8. Use overlay-only controls to match the drawn path to the real motion.
