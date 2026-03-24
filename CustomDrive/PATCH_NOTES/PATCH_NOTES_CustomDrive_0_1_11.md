# PATCH NOTES — CustomDrive 0_1_11

## Request summary
Update the standalone dual-servo tester so it uses channels 0 and 1, with channel 0 driven at 1.5x the requested angle for channel 1, and clamp all angles to the valid 0–180 degree range.

## Root cause / context
The previous dual-servo tester used channels 1 and 2 and applied the same requested angle to both channels in same-direction mode. That did not match the real arm linkage requirement the user clarified afterward.

## Files changed
- `CustomDrive/custom_drive/dual_servo_test.py`
- `CustomDrive/config/dual_servo_test.json`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_11.md`

## Exact behavior changed
- Default channels changed from 1 and 2 to 0 and 1.
- Channel 1 is now the direct requested angle.
- Channel 0 is now computed as `requested_angle * 1.5` in same-direction mode.
- Channel 0 and channel 1 are both clamped to the valid servo range of 0 to 180 degrees.
- Added configurable `channel_a_multiplier` with default `1.5`.
- Info and sweep output now show the scaling behavior clearly.

## Verification actually performed
- Updated code was syntax-checked with `python3 -m compileall` on the patch tree.
- Confirmed clamp helper is still applied to both computed output angles.

## Known limits / next steps
- This tester only validates raw PCA9685 servo output. It does not update the main CustomDrive manual-control arm logic yet.
- If the mechanical linkage needs mirrored motion later, opposite-direction mode may need a different formula than the current simple scaled mirror.
