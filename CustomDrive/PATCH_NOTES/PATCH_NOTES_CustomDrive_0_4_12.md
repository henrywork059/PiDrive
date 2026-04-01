# PATCH NOTES — CustomDrive_0_4_12

## Request summary
Fix the Mission 1 target-follow agreement again because, in live testing, a target shown on the **left** was still causing the car to turn the **wrong way**.

This patch keeps the accepted Mission 1 session web flow, route parsing, model upload/select, AI startup, target-side status, and car-turn status from the latest `0_4_x` line.

## Cause / root cause
The live reports across the last few Mission 1 patches showed that two different left/right problems had been mixed together:

1. **image-side interpretation** of the detected target position
2. **motor steering sign** used to make the car turn toward that target

`0_4_11` mirrored the detected x-ratio to fix the earlier “right looked like left” report, but your latest live test showed the Mission 1 tracker still needed to follow the **displayed frame side directly** and that the **steering sign used in `0_4_9` through `0_4_11` was opposite of the real Mission 1 vehicle behavior**.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_12.md`

## Exact behavior changed
### Mission 1 target-side classification
- removed the Mission 1 x-ratio mirroring introduced in `0_4_11`
- the Mission 1 tracker now classifies target side from the detector's **raw displayed-frame horizontal ratio**
- this keeps `target_side` aligned with the visible frame:
  - left in frame -> `target_side=left`
  - right in frame -> `target_side=right`
  - middle 10% -> `target_side=center`

### Mission 1 steering agreement
- restored the Mission 1 steering sign so it matches the live Mission 1 vehicle behavior:
  - `left` zone -> **positive** steering -> car turn status `left`
  - `right` zone -> **negative** steering -> car turn status `right`
  - `center` zone -> straight forward
- forward motion toward the target is unchanged and still stays active while turning

### Debug detail text
- kept the debug text fields:
  - `raw_x_ratio`
  - `tracking_x_ratio`
- in this patch, `tracking_x_ratio` is intentionally the same as `raw_x_ratio` so it is obvious that no Mission 1 x-mirroring is being applied

## Verification actually performed
- inspected the current `0_4_11` Mission 1 tracking code directly
- reviewed the latest four Mission 1 patch notes (`0_4_8` through `0_4_11`) to avoid rolling back accepted session/UI/model work
- compared the current steering block against the earlier `0_4_8` implementation and your latest live behavior report
- updated only the Mission 1 tracking-side interpretation and steering mapping in `mission1_session_app.py`
- ran Python compile validation on the patched file successfully
- packaged a patch-only zip with the correct top-level `CustomDrive/` folder and no `__pycache__` / `.pyc` files

## Known limits / next steps
- this patch is based on the latest live Mission 1 vehicle behavior you reported
- if a later camera mode or hardware setup genuinely needs mirrored image-side tracking again, the safest future improvement would be a Mission 1-only config toggle instead of another hardcoded flip
- this patch does not change route execution, model loading, camera startup, or target-reached stop logic
