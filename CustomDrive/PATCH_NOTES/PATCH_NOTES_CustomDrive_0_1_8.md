# PATCH NOTES — CustomDrive 0_1_8

## Summary
This patch turns the manual arm control on by default and changes the lift buttons to press-and-hold behavior.

## Changes
- `CustomDrive/config/manual_control.json`
  - set `arm.enabled` to `true`
  - added `lift_step_angle`
- `custom_drive/manual_control_config.py`
  - default arm config now enables the arm
  - normalizes `lift_step_angle`
- `custom_drive/arm_service.py`
  - added background press-and-hold lift motion
  - added stop action
  - status now reports `lift_angle` and `moving`
- `custom_drive/manual_web/static/app.js`
  - `Up` and `Down` now start motion on press and stop on release
  - arm status shows current lift angle
- `custom_drive/manual_web/templates/index.html`
  - updated arm panel helper text
- `custom_drive/manual_control_app.py`
  - bumped app version for cache-busting

## Behavior
- `Up`: lifts only while the button is pressed
- `Down`: lowers only while the button is pressed
- `Hold`: closes / grips once
- `Release`: opens / releases once

## Notes
- The default PCA9685 address remains `0x40` (`64` in JSON).
- Tune `lift_up_angle`, `lift_down_angle`, and `lift_step_angle` for the real arm geometry.
- If the lift direction feels reversed, swap `lift_up_angle` and `lift_down_angle`.

## Verification
- `python -m compileall CustomDrive`
