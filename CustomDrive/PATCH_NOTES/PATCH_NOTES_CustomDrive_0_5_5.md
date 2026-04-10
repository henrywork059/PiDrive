# PATCH NOTES — CustomDrive_0_5_5

## Request summary
Check the current Mission 1 motor logic because movement seemed off.

## Baseline / rollback review
This patch was built forward from the latest accepted Mission 1 patch line available in the workspace:
- `CustomDrive_0_5_4.zip`

Before patching, the recent CustomDrive Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_1.md`
- `PATCH_NOTES_CustomDrive_0_5_2.md`
- `PATCH_NOTES_CustomDrive_0_5_3.md`
- `PATCH_NOTES_CustomDrive_0_5_4.md`

Accepted behavior intentionally preserved:
- start route still runs through the calibrated route-mix path
- pickup / drop-off state machine remains unchanged
- box drawing, detection list, FPS reporting, and arm sequence remain unchanged
- forward and reverse direct-motor behavior remains unchanged
- only the Mission 1 in-place turn path was corrected

## Cause / root cause
The Mission 1 code was using **two different motor-control paths**:

1. Route motion used `MotorService.update(...)`
   - honors `steering_direction`
   - honors left/right motor direction, speed limits, and bias
   - uses the service lock

2. Mission 1 in-place turns used a separate direct-motor helper
   - directly wrote opposite left/right motor values
   - bypassed `steering_direction`
   - bypassed the service lock

That split could make movement feel inconsistent or wrong, especially when the PiServer motor config has a non-default `steering_direction` or other tuning applied. In practice, the typed route could turn one way while Mission 1 search / track turns behaved differently.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_5.md`

## Exact behavior changed

### 1. Mission 1 in-place turns now use the calibrated MotorService path
`_turn_in_place(...)` was changed so it now calls:
- `self.motor_service.update(steering=..., throttle=0.0, steer_mix=1.0)`

This keeps the Mission 1 turn behavior in the same calibrated control path as the route turns.

Result:
- `left` / `right` Mission 1 search turns honor the current PiServer motor calibration
- `steering_direction` now applies to Mission 1 in-place turns too
- opposite motor directions are still used, because `throttle=0` and `steer_mix=1.0` produce a pure spin command

### 2. Direct-motor helper now uses the motor-service lock
The Mission 1 direct-motor helper was also tightened so it now updates the motors under `self.motor_service._lock` before updating the cached last-left / last-right values.

This does not change the intended forward or reverse behavior, but it removes an internal inconsistency where Mission 1 direct motor writes could bypass the shared motor-service lock.

### 3. Last-command reporting now reflects calibrated turn commands
When Mission 1 issues an in-place turn, `last_command` now records:
- `mode = turn_in_place`
- the actual steering value used
- the actual left / right motor values returned by `MotorService.update(...)`

That makes the live status and future debugging more truthful.

## Verification actually performed
The following checks were actually performed:

1. Inspected the actual latest Mission 1 backend in `CustomDrive_0_5_4.zip`.
2. Traced the real Mission 1 motor path and confirmed:
   - route motion used `MotorService.update(...)`
   - Mission 1 in-place turn logic bypassed that calibrated path
3. Inspected the shared PiServer `MotorService` implementation to confirm `steering_direction` is applied inside `update(...)`.
4. Patched only the Mission 1 in-place turn helper and direct-motor lock usage.
5. Ran `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py` successfully.
6. Checked the patch zip structure to ensure it contains only changed/new files plus patch notes, with the top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
- This patch corrects the main Mission 1 turn-path inconsistency, but it does not retune your configured motor speeds or biases.
- If movement still feels off after this patch, the next grounded checks should be:
  1. compare the saved PiServer motor config values (`left_direction`, `right_direction`, `steering_direction`, `left_bias`, `right_bias`)
  2. verify whether the desired search direction should still be clockwise after calibration
  3. optionally add a Mission 1-specific search-direction setting in the web UI
- Forward and reverse still use the direct-motor path by design. That was left unchanged in this patch because your Mission 1 requirement explicitly wanted in-place turning to use opposite motor directions.
