# PATCH NOTES — CustomDrive_0_5_2

## Request summary
Patch Mission 1 so it becomes a looping pickup/drop-off state machine instead of a single fixed-target grip demo.

The requested Mission 1 behavior for this patch was:

1. The car still runs the typed start route first to move into the target search area.
2. After the route, the car turns on the camera and keeps the AI model running frame-by-frame.
3. During **pickup search**:
   - if no class `1` or `2` is detected, the car rotates **clockwise** to search
   - if one class `1` or `2` is detected, it locks onto that as the pickup target and moves toward it
   - if multiple class `1` / `2` targets are detected, it moves toward the **nearest** pickup target and locks onto that target class
4. When the pickup target is close enough using the existing Mission 1 closeness rule, the arm sequence should be:
   - **Grip ready**
   - **Grip**
   - **Grip and lift**
5. After pickup, the session should save state to remember whether the car is holding class `1` or class `2`.
6. The next search target should depend on what is being held:
   - holding `1` -> search for class `3`
   - holding `2` -> search for class `4`
7. During **drop-off search**:
   - if no class `3` / `4` target is found, rotate **clockwise** to search
   - if the mapped drop-off class is found, move toward it
8. When close enough to the drop-off area:
   - load the **Release** pose
   - update state so the car is no longer holding the pickup object
   - drive backward
   - restart the class `1` / `2` pickup search process
9. Keep patch notes detailed and careful for future development.
10. Be careful not to introduce foldering/naming mistakes or rollback accepted Mission 1 behavior.

## Baseline / rollback review
This patch is intended to build forward from the user's current accepted CustomDrive line after `0_5_1`.

In this environment, the uploaded `CustomDrive_0_5_0.zip` itself was not directly accessible through the container filesystem during patching, so the working Mission 1 state used for this patch was reconstructed from the **accessible current code** plus the accepted Mission 1 patch line that is available in the container:
- repo `CustomDrive/` snapshot from `PiDrive-main.zip`
- `CustomDrive_0_4_13.zip`
- `CustomDrive_0_4_14.zip`
- `CustomDrive_0_4_15.zip`
- `CustomDrive_0_4_16.zip`
- `CustomDrive_0_5_1.zip`

Before patching, the latest visible Mission 1 patch notes were reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_4_14.md`
- `PATCH_NOTES_CustomDrive_0_4_15.md`
- `PATCH_NOTES_CustomDrive_0_4_16.md`
- `PATCH_NOTES_CustomDrive_0_5_1.md`

Accepted Mission 1 behavior intentionally preserved in this patch:
- typed start route still runs first
- camera still starts after the route
- AI model still loads after the camera is live
- per-frame detector loop remains active on the Pi
- detected-object list, coordinates, confidence, and FPS reporting stay in the web GUI
- Pi-side annotated frame and web overlay boxes remain in place
- Mission 1 arm role mapping and numbered arm poses from `0_5_1` remain supported
- patch is additive to Mission 1 logic and does not replace older CustomDrive manual/generic web apps

## Cause / root cause
The existing Mission 1 code already handled:
- route -> camera -> model -> frame-by-frame AI loop
- one active target class
- arm grip-ready / grip / grip-and-lift sequence

But it did **not** yet implement the larger mission loop the user requested.

### Main gap in the existing code
The current Mission 1 path still behaved like a single-target pursuit flow:
- one configured target class ID
- approach target
- grip / lift
- stop holding position

It did not yet have a real staged mission loop for:
- pickup search over classes `1/2`
- remembering which class is being held
- switching the drop-off target based on the held class
- searching for drop-off classes `3/4`
- release + reverse + restart pickup search

### Why a state-machine patch was required
Trying to keep patching the earlier “single target class” flow would keep forcing one-off branches and would make the logic fragile.

The correct fix for this request was to make Mission 1 behave like a simple state machine with these stages:
- pickup search
- pickup track
- pickup capture
- drop-off search
- drop-off track
- reverse reset

That state layer is what this patch adds.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_2.md`

## Exact behavior changed

### 1. Mission 1 now runs a pickup/drop-off loop instead of a single fixed target class
Mission 1 still performs the same startup order:
- load starting arm pose
- run the typed start route
- start the camera
- load the selected AI model

After that, the AI loop now behaves as a two-stage mission cycle:
- **pickup stage**: search class `1` / `2`, approach, grip, lift
- **drop-off stage**: search mapped class `3` / `4`, approach, release, reverse, restart pickup search

### 2. Pickup search now uses classes 1 and 2
During pickup search, the Mission 1 loop now treats classes `1` and `2` as valid pickup targets.

If there is:
- **no class `1/2`** -> rotate clockwise to search
- **one class `1/2`** -> lock pickup to that class and move toward it
- **multiple class `1/2` targets** -> choose the **nearest** one (implemented as the largest visible box area, then confidence as tie-breaker)

Once a pickup target class is selected, the current Mission 1 cycle stores that class in `pickup_target_class_id` until the pickup stage completes or the search resets.

### 3. Clockwise search rotation is now automatic when the required target is not visible
For both pickup and drop-off stages, when the required class is not visible the car now rotates clockwise automatically.

In this patch, the code-level clockwise search command is implemented as the Mission 1 right-turn in-place command using opposite motor directions.

This does **not** change the accepted left/right turning logic elsewhere in Mission 1; it only applies the existing turn command as the automatic search behavior when no required target is found.

### 4. Pickup capture now stores which class the car is holding
When the pickup target becomes close enough using the existing Mission 1 closeness condition:
- target is in the forward path (`|x| < deadband`)
- target `y` is below the configured trigger line (`y < -frame_height * grip_trigger_y_ratio`)

Mission 1 now:
- stops the motors
- loads **Grip**
- loads **Grip and lift**
- stores the held pickup class in `held_class_id`
- computes the matching drop-off class and stores it in `dropoff_target_class_id`
- switches the mission state into drop-off search

### 5. Drop-off target selection now depends on the held class
The Mission 1 loop now uses this mapping:
- holding class `1` -> target drop-off class `3`
- holding class `2` -> target drop-off class `4`

That mapping is stored under the Mission 1 config `mission.dropoff_map` and defaults to:
- `1 -> 3`
- `2 -> 4`

### 6. Drop-off search now approaches the mapped drop-off class
After pickup, the car does **not** stop permanently anymore.

Instead, it now enters a drop-off search loop:
- if the mapped drop-off class is not visible -> rotate clockwise to search
- if the mapped drop-off class is visible -> move toward it using the same centered-x forward / signed-x turning rule already used in Mission 1

### 7. Release + reverse + pickup-search restart are now automatic
When the mapped drop-off class is close enough using the same closeness rule:
- stop the motors
- load the **Release** pose
- clear the held-class state
- reverse for a short configured duration
- load the **starting position** arm pose again
- restart pickup search for class `1/2`

This gives Mission 1 a real repeated pickup/drop-off loop instead of ending after grip-and-lift.

### 8. Mission 1 now tracks and reports the loop state explicitly
The Mission 1 backend now reports these extra mission-state fields in `/api/status`:
- `mission_state`
- `held_class_id`
- `dropoff_target_class_id`
- `pickup_target_class_id`
- `pickup_classes`

The web UI now surfaces this in the summary/status area so the operator can see:
- whether the loop is in pickup search, pickup track, drop-off search, drop-off track, or reverse reset
- what class is currently being held
- what drop-off class is currently being searched
- which pickup class is currently locked

### 9. Mission 1 viewer/status text now describes the real current loop
The Mission 1 web text was updated so it no longer describes the session as only a single-target grip flow.

The page now explains that the current Mission 1 loop:
- searches class `1/2` for pickup
- grips/lifts the selected pickup class
- searches class `3/4` depending on the held class
- releases, reverses, and restarts pickup search

### 10. Existing accepted Mission 1 features were intentionally preserved
This patch does **not** remove or redesign these accepted Mission 1 parts:
- typed start-route support
- model upload / model selection flow
- detector FPS reporting
- Pi-side annotated frame generation
- web-side overlay box drawing
- detection table with coordinates / confidence / box size
- numbered 3-servo pose editor
- arm role mapping for starting / grip ready / grip / grip and lift / release

## Verification actually performed
The following checks were actually performed:

1. Inspected the accessible current Mission 1 code and merged Mission 1 patch line before editing.
2. Reviewed the recent Mission 1 patch notes to reduce rollback risk:
   - `0_4_14`
   - `0_4_15`
   - `0_4_16`
   - `0_5_1`
3. Patched the Mission 1 backend state flow in `mission1_session_app.py` to support pickup/drop-off looping.
4. Updated the Mission 1 web status/view text in:
   - `mission1_web/templates/index.html`
   - `mission1_web/static/app.js`
5. Ran Python compile validation successfully on the patched backend file:
   - `python -m py_compile custom_drive/mission1_session_app.py`
6. Ran JavaScript syntax validation successfully on the patched web script:
   - `node --check custom_drive/mission1_web/static/app.js`
7. Ran `python -m compileall` successfully on the patched CustomDrive workspace.
8. Attempted an import-level smoke test of `Mission1SessionContext`, but the container environment does not have `flask` installed, so a full runtime import test could not be completed here.
9. Confirmed the patch zip is patch-only, keeps the top-level `CustomDrive/` folder, and does **not** include `__pycache__` or `.pyc` files.

## Known limits / next steps
1. This patch was verified at code/syntax level, but it was **not** tested here on the real Pi hardware with the real camera, real motors, and the user's deployed TFLite model.
2. “Nearest target” is currently implemented as the detection with the **largest visible box area**, which is a practical approximation of nearest object distance. If the mission later needs a different rule, this can be extended.
3. Clockwise search is implemented using the existing Mission 1 in-place right-turn command. If the physical robot wiring/config makes that spin the opposite physical direction, the logic-level behavior is still correct in code but the Pi motor runtime config may still need adjustment.
4. The old `session.target_class_id` field is now effectively a legacy compatibility field in the Mission 1 config/UI. The current pickup/drop-off loop uses classes `1/2` and the `1->3`, `2->4` mapping instead.
5. This patch does not yet add a separate editable web panel for mission loop parameters like:
   - search rotation speed
   - reverse-after-release duration
   - reverse speed
   These are normalized in code for now and can be exposed later if needed.
6. This patch uses class-based locking, not full per-object visual tracking across frames. If multiple same-class targets overlap or swap positions, the loop may re-lock to the largest visible same-class target.
