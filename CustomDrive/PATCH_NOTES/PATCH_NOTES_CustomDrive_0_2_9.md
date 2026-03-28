# CustomDrive 0_2_9 Patch Notes

## Request summary
Fix the lift path because servo 0 appeared released and did not respond to the Up/Down buttons, while Open/Close on servo 2 was already working.

## Cause / root cause
The lift path was not explicitly reasserting the current lift angle on startup/reload or after stopping lift motion. That could leave servo 0 effectively unheld after earlier tests or after button release, even though the gripper path on servo 2 still worked.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`

## Exact behavior changed
- Lift startup/reload now immediately applies the configured current lift angle to the lift channels.
- Lift stop now reapplies the current lift angle instead of just ending the worker thread.
- This keeps servo 0 held/powered after releasing the Up/Down buttons.
- Open/Close gripper behavior on servo 2 was left unchanged.

## Verification actually performed
- Patched forward from the `CustomDrive_0_2_0` stable baseline.
- Python compile check on the changed file.

## Known limits / next steps
- This patch does not change GUI bindings or gripper logic.
- If servo 0 still does not move after this patch, the next check should be whether the Pi-side runtime is using an older local file instead of the patched `arm_service.py`.
