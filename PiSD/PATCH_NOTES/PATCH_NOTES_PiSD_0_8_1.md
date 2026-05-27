# PATCH NOTES - PiSD_0_8_1

## Request summary

User requested a targeted PiSD patch based on the current stable `PiSD_0_8_0` package to:

1. Remove `turn_gain` from real motor steering.
2. Keep `turn_curve` as the motor steering response tuning value.
3. Keep overlay tuning separate from motor tuning so the overlay can be manually matched to real vehicle motion.
4. Bring the Motor Tuning page style into line with the rest of the PiSD UI.
5. Add the live camera frame to the Motor Tuning overlay preview so the user can draw the overlay on top of the real camera view while matching it to actual car motion.

## Cause / root cause

`PiSD_0_8_0` still used `turn_gain` in the `turn_rate` motor calculation:

```text
turn_mag = abs(steering) ** turn_curve * turn_gain
```

With the default `turn_gain = 0.75`, full steering did not reach the physical tightest non-pivot turn. The inside wheel still moved at about 25% of the outside wheel speed. This conflicted with the simplified steering model where `steering = +/-1` should represent the tightest non-pivot curve.

The overlay was also coupled to motor turn-rate settings, so visual path shape could change when motor steering settings changed. The requested behaviour is that the overlay remains a visual/manual calibration layer that is matched against real motion, not a second motor-control parameter path.

The Motor Tuning page also used its own large visual layout and an SVG-only preview surface, which made it less consistent with Manual Drive/Settings and prevented overlay calibration against the live camera image.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/config/defaults.json`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/js/motor_tuning.js`
- `PiSD/pisd/web/static/css/motor_tuning.css`
- `PiSD/pisd/web/static/js/overlay_geometry.js`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/static/css/pisd_design_system.css`
- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/README.md`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/SETTINGS_MANAGER.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/scripts/test_motor_steering_modes.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/scripts/test_overlay_turn_rate_geometry.js`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_1.md`

## Behaviour changed

### Motor steering

- Removed `turn_gain` from the active `turn_rate` motor steering formula.
- New motor formula:

```text
turn_mag = abs(steering) ** turn_curve
```

- `turn_curve` remains the motor response-shaping value.
- With default `min_inside_speed = 0.0`, full steering now gives:

```text
outside wheel = throttle
inside wheel = 0
```

- Legacy persisted `turn_gain` values are ignored and removed from normalised runtime settings so old settings files do not break startup or UI loading.
- `arcade_mix` fallback remains available.
- Optional pivot behaviour remains available only when `allow_pivot_turn` is explicitly enabled.

### Motor-setting UI

- Removed active `Turn Gain` inputs from:
  - Settings page
  - Testing page
  - Motor Tuning page
- Settings normalisation now deletes legacy `turn_gain` before returning settings to the UI.

### Overlay calibration

- Overlay turn-rate drawing is now visual-only and manually tunable.
- Overlay geometry no longer uses motor `turn_gain` or motor `turn_curve` to shape the visual path.
- Overlay path shaping uses visual calibration values such as:
  - `curve_response`
  - `turn_rate_visual_scale`
  - `curve_strength`
  - `curvature_scale`
  - projection and width controls
- Motor `Turn Curve` changes real wheel-speed mapping only. It does not automatically change the overlay path.
- Manual Drive and AI Mode keep using the shared overlay renderer, but the renderer now treats the path as a visual calibration layer.

### Motor Tuning page live camera overlay

- The Motor Tuning overlay panel now has a real camera image underneath the SVG overlay.
- Added camera controls:
  - `Start camera + live`
  - `Snapshot frame`
  - `Stop camera only`
- The page attempts to start the live camera preview on load.
- The overlay SVG is drawn above the camera frame for direct visual matching against the real view.
- Camera controls do not move the car. Motor movement still requires the safety checkboxes and the existing timed test buttons.

### Motor Tuning page presentation

- Reordered Motor Tuning CSS loading to match the shared PiSD style stack:
  - page CSS
  - unified layout
  - design system
  - responsive layout system
- Added Motor Tuning selectors to the shared design/layout system so its panels, buttons, code pills, shell width, and responsive layout match the other PiSD pages more closely.
- Motor Tuning now uses a shared two-column responsive layout:
  - live camera overlay as the main preview region
  - safety and motion controls in the control column
  - motor and overlay settings below
  - log panel full-width at the bottom

## Compatibility notes

- Existing `runtime_settings.json` files that still contain `motor.turn_gain` are safe. The key is ignored and removed from normalised runtime settings.
- Existing overlay calibration values remain preserved.
- Existing `turn_curve`, `min_inside_speed`, `allow_pivot_turn`, `steer_mix`, motor direction, max speed, and bias values are preserved.
- The patch does not reset camera settings or user overlay settings.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/overlay_geometry.js
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
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
- Straight steering still produced equal wheel outputs.
- Optional pivot mode still works when explicitly enabled.
- Settings persistence test confirmed legacy `turn_gain` is ignored and not returned in normalised motor settings.
- Overlay geometry test confirmed visual overlay scale/curve response are controlled by overlay settings rather than motor `turn_gain` or motor `turn_curve`.
- Status-only launch reports PiSD version `0.8.1` and motor status no longer includes `turn_gain`.

## Verification not performed / known limits

- Full Flask route test for `scripts/test_motor_tuning_page.py` without `--static-only` could not be completed in this container because Flask is not installed here (`PISD-APP-002`). Static source checks and non-Flask service tests were completed.
- Real Raspberry Pi camera preview and real motor movement were not hardware-tested in this environment.
- The live Motor Tuning camera overlay should be verified on the Pi by opening `/motor-tuning`, confirming the stream appears under the overlay, then running short safe tests while adjusting overlay values.

## Suggested Pi-side test sequence

1. Apply this patch over `PiSD_0_8_0`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open:

```text
http://<pi-ip>:5050/motor-tuning
```

4. Confirm the live camera frame appears under the overlay.
5. Lift the wheels or clear a safe area.
6. Tick the safety acknowledgements only when ready for real motor output.
7. Run short left/right turn tests.
8. Use overlay-only controls, especially `Turn-rate visual scale` and `Visual curve response`, to match the drawn road path to the real turn shown by the camera.
