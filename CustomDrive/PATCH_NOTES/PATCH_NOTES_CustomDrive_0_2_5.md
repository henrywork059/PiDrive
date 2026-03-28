# CustomDrive 0_2_5 Patch Notes

## Request summary
Ensure the arm open/close actions only control servo channel 2 among servos 0, 1, and 2.

## Root cause
The gripper channel was configurable, so an incorrect or overlapping setting could cause open/close actions to target the wrong servo.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/config/manual_control.json`

## Exact behavior changed
- Gripper actions now always use servo channel 2.
- Manual-control config normalization now forces `grip_channel` to `2`.
- Arm status now reports grip channel 2 consistently.
- Default manual-control config remains aligned with lift on channels 0 and 1, gripper on channel 2.

## Verification performed
- Reviewed the current 0_2_0 baseline and the recent 0_2_1 to 0_2_4 patches before editing.
- Ran `python -m compileall CustomDrive` on the patched tree.

## Known limits / next steps
- This patch only fixes channel routing. It does not retune grip angles or servo speed.
