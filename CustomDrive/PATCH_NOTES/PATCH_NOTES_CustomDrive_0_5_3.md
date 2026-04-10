# PATCH NOTES — CustomDrive_0_5_3

## Request summary
Fix the new Mission 1 pickup/drop-off loop because the car seems not to move after it has picked up the object.

The immediate user report for this patch was:
- after the car picks up the object, it seems not to move

The intent of the already accepted `0_5_2` mission flow remains:
- run the typed route first
- turn on camera
- search for pickup classes `1/2`
- grip and lift the pickup target when close enough
- remember the held class
- search for the mapped drop-off class (`1 -> 3`, `2 -> 4`)
- release, reverse, and restart pickup search

## Baseline / rollback review
This patch is built forward from the latest accepted Mission 1 patch line available in the container:
- `CustomDrive_0_5_2.zip`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_4_16.md`
- `PATCH_NOTES_CustomDrive_0_5_1.md`
- `PATCH_NOTES_CustomDrive_0_5_2.md`

Accepted Mission 1 behavior intentionally preserved:
- start route still runs before camera/model startup
- camera and model startup order is unchanged
- pickup search still uses classes `1/2`
- nearest pickup target logic still stays in place
- grip-ready / grip / grip-and-lift sequence is unchanged
- held-class and drop-off mapping logic is unchanged
- drop-off search / release / reverse / restart behavior remains in place
- no changes were made to the Mission 1 web layout or detection overlay path

## Cause / root cause
The `0_5_2` Mission 1 state machine changed state correctly after pickup, but the handoff from **pickup capture** to **drop-off search** still left the motors stopped until the *next* AI loop iteration produced a new movement command.

### What the code was doing before this patch
After the pickup target became close enough, `0_5_2` did this sequence:
1. stop the motors
2. load **Grip**
3. load **Grip and lift**
4. mark the held class
5. switch the session state to `dropoff_search`
6. wait for the next detection-loop cycle to decide whether to rotate or track the drop-off target

That means the pickup branch itself did **not** issue an immediate post-pickup search command.

### Why this looked like “the car is not moving after pickup”
Because the motors had already been stopped for the grip sequence, the car could remain visibly stationary right after pickup until the next AI frame/cycle reached the drop-off search logic.

On a real Pi this can look like the mission stalled even though the state had technically changed.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_3.md`

## Exact behavior changed

### 1. Mission 1 now starts drop-off search motion immediately after pickup
After:
- `Grip`
- `Grip and lift`
- held-class save
- drop-off target mapping

Mission 1 now immediately issues a **clockwise search rotation** command for the mapped drop-off class in the same pickup-capture branch.

So the handoff is now:
- pickup capture complete
- object marked as held
- state set to `dropoff_search`
- car immediately begins rotating clockwise to search the drop-off area

This removes the visible “stopped after pickup” gap.

### 2. Status fields are set consistently during the immediate handoff
The pickup-complete branch now also explicitly sets:
- `target_found = False`
- `target_side = 'search'`
- `car_turn_direction = 'right'`
- `arm_target_lock_engaged = False`

before issuing the search rotation.

This keeps the runtime status payload aligned with the movement command that is sent immediately after pickup.

## Verification actually performed
The following checks were actually performed in the patch workspace:

1. Opened the actual `0_5_2` Mission 1 backend and traced the pickup -> drop-off handoff.
2. Confirmed that the original pickup-complete branch changed the mission state but did not issue an immediate movement command.
3. Patched only the Mission 1 pickup-complete branch.
4. Ran:
   - `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`
5. Packaged a patch-only zip with:
   - top-level `CustomDrive/` folder
   - changed file plus patch notes only
   - no `__pycache__`
   - no `.pyc`

## Known limits / next steps
1. This patch fixes the immediate post-pickup motion handoff, but it does **not** redesign the rest of the mission controller.
2. If the drop-off search still feels too weak on hardware, the next useful patch would be to add:
   - a short configurable post-lift pause
   - a configurable post-lift search rotation duration
   - a visible mission-state banner for pickup/drop-off transitions
3. This patch does not change the drop-off target selection rule itself.
4. Physical behavior still depends on the Pi's current motor runtime config and wiring direction.
