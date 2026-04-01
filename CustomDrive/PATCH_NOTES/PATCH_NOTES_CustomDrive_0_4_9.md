# PATCH NOTES — CustomDrive_0_4_9

## Request summary
Adjust the Mission 1 target-finding behavior so the turn direction agrees with the target position rule:
- target centre on the left -> turn left
- target centre on the right -> turn right
- target centre in the middle 10% -> go forward

This was requested as a forward patch on top of the Mission 1 session web GUI work.

## Cause / root cause
The Mission 1 tracker in `CustomDrive_0_4_8` correctly split the frame into left / center / right zones, but the steering sign assigned to the left and right zones was reversed in the target-follow block. That made the car steer away from the detected target instead of toward it.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_9.md`

## Exact behavior changed
- In Mission 1 AI tracking:
  - left zone now sends a left-turn steering command while continuing forward
  - right zone now sends a right-turn steering command while continuing forward
  - center zone behavior is unchanged and still goes straight forward within the middle-band rule
- No route parsing, camera startup, model loading, upload flow, or target-reached logic was changed in this patch.

## Verification actually performed
- Inspected the Mission 1 follow-target code from the previous patch.
- Confirmed the zone selection logic was already correct and only the turn-command mapping needed to change.
- Updated only the left/right steering mapping in `mission1_session_app.py`.
- Ran Python compile validation on the patched file successfully.
- Packaged a patch-only zip with the top-level `CustomDrive/` folder and no `__pycache__` / `.pyc` files.

## Known limits / next steps
- Live physical turn direction still depends on the shared motor runtime configuration on the Pi, especially if steering-direction inversion is changed in saved motor settings.
- This patch fixes the Mission 1 code-level agreement rule, but final on-car validation should still be done with the actual model and hardware.
