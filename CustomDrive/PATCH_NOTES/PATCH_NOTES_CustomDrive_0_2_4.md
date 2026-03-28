# PATCH NOTES — CustomDrive_0_2_4

## Request summary
- Set a default arm position and clamp position to 90°.
- Increase the arm movement speed by 100%.

## Cause / root cause
- The arm service initialized the lift state from `lift_down_angle` and did not actively drive the arm or clamp to a dedicated default angle on startup.
- The press-and-hold lift loop was still using a 0.1s step interval, so motion remained at 1° per 0.1s.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/config/manual_control.json`

## Exact behavior changed
- Added explicit startup/default positions for the arm:
  - `lift_default_angle = 90`
  - `grip_default_angle = 90`
- On arm-service reload/init, the service now applies those defaults to the configured lift servo(s) and grip servo when the PCA9685 backend is available.
- Doubled lift motion speed by changing the default `lift_step_interval_s` from `0.1` to `0.05` while keeping `lift_step_angle = 1`.
- Updated the default manual-control config to store the same values.

## Verification performed
- Updated the stable `CustomDrive_0_2_0` baseline forward without touching unrelated GUI layout files.
- Ran `python -m compileall CustomDrive`.

## Known limits / next steps
- Real servo movement at startup still depends on the Pi having working PCA9685/I2C access and the configured channels matching the hardware.
- If the physical linkage should not start at 90°, change `lift_default_angle` or `grip_default_angle` in `CustomDrive/config/manual_control.json`.
