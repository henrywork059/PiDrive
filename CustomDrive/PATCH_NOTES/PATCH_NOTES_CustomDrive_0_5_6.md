# PATCH NOTES — CustomDrive_0_5_6

## Request summary
Fix the bugs in the Mission 1 **start routing movement and motor logic** and deliver a forward patch.

The specific problem identified in the current Mission 1 code was that the **start route** was still using an older hardcoded steering/throttle path, while the newer Mission 1 search / pickup / drop-off logic was using the newer movement helpers and tuning.

This made the car movement feel inconsistent because:
- the typed start route used fixed hardcoded motion values
- the live Mission 1 pursuit logic used configurable Mission 1 movement values
- route turns were tied to the older `steer_mix` route path instead of the newer Mission 1 turn helper

## Baseline / rollback review
This patch was built forward from the latest accepted Mission 1 patch line available in the workspace:
- `CustomDrive_0_5_5.zip`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_2.md`
- `PATCH_NOTES_CustomDrive_0_5_3.md`
- `PATCH_NOTES_CustomDrive_0_5_4.md`
- `PATCH_NOTES_CustomDrive_0_5_5.md`

Accepted behavior intentionally preserved:
- typed start route syntax remains the same
  - `--forward SECONDS`
  - `--backward SECONDS`
  - `--turn-right SECONDS`
  - `--turn-left SECONDS`
- route step order still follows the exact order typed by the user
- Mission 1 pickup / drop-off state machine from `0_5_2` onward remains unchanged
- post-pickup immediate drop-off search from `0_5_3` remains unchanged
- reduced x deadband from `0_5_4` remains unchanged
- calibrated in-place turn path from `0_5_5` remains unchanged and is now also reused by start-route turning
- arm logic, detection loop, model load, box drawing, and FPS reporting remain unchanged

## Cause / root cause
The current Mission 1 start route was still implemented using the older route-step fields:
- `steering`
- `throttle`

and `_run_start_route()` repeatedly called:
- `_set_route_drive(steering, throttle, note)`

### Why that was a problem
The rest of the Mission 1 movement system had already evolved to use:
- `_drive_forward(...)`
- `_turn_in_place(...)`
- `turn_k`
- `turn_speed_max`
- `search_rotate_speed`
- direct forward / reverse helpers

So there were effectively **two movement systems** active in the same Mission 1 session:

1. **Start route movement**
   - hardcoded values from `parse_route_text()`
   - `--forward` always used throttle `0.22`
   - `--backward` always used throttle `-0.18`
   - `--turn-left/right` always used steering `±0.9` through the older route-mix path

2. **Live Mission 1 movement after the route**
   - used the newer Mission 1 motion helpers and tuning
   - used calibrated in-place turn helper after `0_5_5`
   - used configurable forward speed / turn gain / turn max

That split is what made the route movement feel “off” compared with the rest of the session.

### Main root causes fixed in this patch
1. **Hardcoded route movement values** were still embedded in `parse_route_text()`.
2. **Route execution** still used the older mixed steering/throttle path instead of the newer Mission 1 helpers.
3. **Start-route turning** was not using the same Mission 1 calibrated in-place turn helper as the live search / tracking loop.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_6.md`

## Exact behavior changed

### 1. Start-route execution now uses Mission 1 movement helpers instead of the older route-mix path
`_run_start_route()` no longer drives the route by repeatedly replaying hardcoded `steering` / `throttle` values.

Instead, each route step now uses the same style of helpers used elsewhere in Mission 1:
- `forward` -> `_drive_forward(...)`
- `backward` -> `_drive_backward(...)`
- `turn-left` -> `_turn_in_place('left', ...)`
- `turn-right` -> `_turn_in_place('right', ...)`

This makes the typed start route feel much more consistent with the rest of the Mission 1 session.

### 2. Start-route turning now reuses the calibrated Mission 1 in-place turn logic
Route turning now uses `_turn_in_place(...)`, which after `0_5_5` already routes through:
- `MotorService.update(...)`
- current `steering_direction`
- current shared motor tuning / calibration

This means the start route and the live Mission 1 search / tracking loop now use the **same turn path** instead of two different turn implementations.

### 3. Hardcoded route speed values were removed from the route parser
`parse_route_text()` no longer bakes movement power directly into each route step.

Instead, it now stores only the route motion type and duration:
- forward
- backward
- turn_left
- turn_right

This avoids hiding movement power inside the parser and lets the route executor use the current Mission 1 settings at runtime.

### 4. Start-route motion is now driven by Mission 1 route speed settings
A route-speed layer was added under the Mission 1 `mission` config:
- `route_forward_speed`
- `route_backward_speed`
- `route_turn_speed`

Defaults used in this patch:
- `route_forward_speed = 0.22`
- `route_backward_speed = 0.18`
- `route_turn_speed = 0.75`

Fallback behavior:
- route forward speed defaults to `drive.forward_speed`
- route backward speed defaults to `mission.reverse_speed`
- route turn speed defaults to `drive.turn_speed_max`

This gives the route its own explicit movement tuning instead of depending on the older hidden hardcoded values.

### 5. Route status now reflects the actual motion being executed
During the start route, the session now updates the live direction fields more truthfully:
- forward step -> `car_turn_direction = forward`
- backward step -> `car_turn_direction = backward`
- turn-left step -> `car_turn_direction = left`
- turn-right step -> `car_turn_direction = right`

This makes debugging the route behavior easier because the live Mission 1 status now reflects the real route motion.

### 6. Backward route motion now has its own explicit helper
A new helper was added:
- `_drive_backward(...)`

This keeps route backward motion aligned with the direct-motor forward/reverse helpers instead of encoding backward only as a negative throttle constant in the older route-mix path.

## Verification actually performed
The following checks were actually performed in the patch workspace:

1. Reconstructed the current accessible CustomDrive Mission 1 workspace by layering the repo snapshot plus the accepted Mission 1 patch line through `0_5_5`.
2. Reviewed recent patch notes `0_5_2` through `0_5_5` before editing to reduce rollback risk.
3. Inspected the actual current Mission 1 code path and confirmed:
   - `parse_route_text()` still used hardcoded route movement values
   - `_run_start_route()` still used `_set_route_drive(...)`
   - start-route movement did not match the newer Mission 1 movement helpers
4. Patched `mission1_session_app.py` so route parsing stores motion type + duration instead of hidden route power values.
5. Patched `_run_start_route()` so it now uses:
   - `_drive_forward(...)`
   - `_drive_backward(...)`
   - `_turn_in_place(...)`
6. Added explicit route speed config normalization for:
   - `mission.route_forward_speed`
   - `mission.route_backward_speed`
   - `mission.route_turn_speed`
7. Ran:
   - `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`
   - `python -m compileall CustomDrive`
8. Packaged a patch-only zip with:
   - top-level `CustomDrive/` folder
   - changed file plus patch notes only
   - no `__pycache__`
   - no `.pyc`

## Known limits / next steps
1. This patch fixes the **start-route logic mismatch**, but it does not yet add web controls for the new route speed settings.
   - the new route-speed keys are normalized in config and can be edited in config now
   - a later patch can expose them in the Mission 1 web UI if wanted
2. Route forward / backward still use the direct equal-left/right motor helper by design.
   - this is consistent with the current Mission 1 forward/reverse helper logic
   - this patch intentionally did not redesign straight-line motor balancing or add closed-loop correction
3. `_set_route_drive(...)` remains in the file for compatibility/reference, but the start-route executor no longer relies on it.
4. If movement still feels physically off after this patch, the next grounded checks should be:
   - verify current Pi motor config (`left_direction`, `right_direction`, `steering_direction`, biases)
   - compare route timing versus real-world turn angle on the floor
   - optionally expose `route_forward_speed`, `route_backward_speed`, and `route_turn_speed` in the Mission 1 web UI
