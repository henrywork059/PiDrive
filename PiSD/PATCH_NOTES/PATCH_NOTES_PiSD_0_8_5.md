# PiSD 0.8.5 Patch Notes

## Request summary

This patch continues from `PiSD_0_8_4` and applies the requested Motor Tuning and motor-output refinements:

1. Add a configurable motor start dead-zone kick because the motors need more torque to start from static than to keep moving.
2. Reduce the Motor Tuning left-column width by using two equal desktop columns.
3. Make the Motor Tuning live overlay use the same visual style as the Manual Drive overlay.

## Cause / root cause

- The previous motor output path sent the requested low PWM value directly. On small DC motors, a low value may be enough to keep the wheel moving but not enough to overcome static friction from rest.
- The Motor Tuning page layout had unequal desktop columns, making one side feel too wide.
- The Motor Tuning overlay used its own simpler SVG style while Manual Drive used the newer green road-edge / blue centre-arrow road-guide style.

## Files changed

- `PiSD/config/defaults.json`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/js/motor_tuning.js`
- `PiSD/pisd/web/static/css/motor_tuning.css`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/scripts/test_motor_steering_modes.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_5.md`

## Behavior changed

### Motor start dead-zone kick

New motor settings:

- `motor.start_deadzone`
- `motor.start_kick_seconds`

When a wheel starts from static and the requested hardware PWM magnitude is below `start_deadzone`, PiSD now briefly sends that wheel at the configured dead-zone magnitude, then automatically returns to the requested lower value.

Important details:

- The kick is applied at the hardware-output layer only.
- The intended motor output remains the requested logical value.
- The recorded/visible intent remains the real command value, so AI labels are not changed by the start kick.
- Setting `start_deadzone` to `0.0` disables the feature.
- Setting `start_kick_seconds` to `0.0` also disables the feature.
- `stop()` cancels any pending kick timer and sends zero to both motors.

### Motor Tuning page layout

- Desktop layout now uses two equal columns: `1fr / 1fr`.
- The live preview remains compact and is capped to a smaller calibration size.

### Motor Tuning overlay style

- The tuning overlay now uses the Manual Drive style:
  - green road-edge guide lines
  - blue centre direction arrow
  - matching road surface gradient
  - matching reverse/stop visibility behavior
- The overlay still uses the same visual-only calibration settings saved under `manual_drive.overlay`.
- Overlay tuning still does not change the real motor algorithm.

## Compatibility / migration notes

- Existing runtime settings remain compatible.
- If old settings do not contain `start_deadzone` or `start_kick_seconds`, defaults are filled safely.
- The default `start_deadzone` is `0.0`, so existing cars behave the same until the user enables the kick.
- Existing linear X steering from `0.8.2` is preserved.
- Existing intended-output display from `0.8.3` is preserved.
- Manual Drive steer-strength removal from `0.8.4` is preserved.

## Verification actually performed

From the patched `PiSD` folder, these checks were run successfully:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/settings_tab.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Additional note:

- `python3 scripts/test_motor_tuning_page.py` without `--static-only` was attempted but could not complete because Flask is not installed in this container environment. This is an environment limitation, not a verified hardware/runtime failure.

## Hardware testing

Hardware camera/motor testing was not run in this environment.

## Known limits / next steps

- The start dead-zone value must be tuned on the real car. Start with a low value and increase until the wheels reliably start moving, then reduce slightly if the kick is too sharp.
- The kick is intentionally short and does not change AI labels. If real testing shows the kick affects the first few video frames too strongly, the next patch could optionally mark kick-active frames in recording metadata.
