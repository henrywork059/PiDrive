# PATCH NOTES — CustomDrive_0_5_1

## Request summary
Add Mission 1 arm control logic into the current CustomDrive web-session code, using the uploaded `CustomDrive_0_5_0.zip` as the new stable baseline.

The requested behavior for this patch was:

1. In the Mission 1 web GUI, define numbered arm positions by setting the angles of **3 servos** for position numbers such as `1 / 2 / 3 / 4 / ...`.
2. In the Mission 1 web GUI, choose which saved position number is used for these named Mission 1 arm roles:
   - **starting position**
   - **grip ready**
   - **grip**
   - **grip and lift**
   - **release**
3. Load the **starting position** when the Mission 1 session starts.
4. When the Pi first locates the target class object, load **grip ready**.
5. When the target is in the forward path **and** `y < -30%`, load **grip**.
6. After that, load **grip and lift**.
7. Keep the patch detailed and safe for future development, and make sure foldering/naming is correct.

## Baseline / rollback review
This patch was built forward from the user-uploaded `CustomDrive_0_5_0.zip` baseline.

Before patching, the CustomDrive Mission 1 line was reviewed against the latest available Mission 1 patch-note history in the zip:
- `PATCH_NOTES_CustomDrive_0_4_13.md`
- `PATCH_NOTES_CustomDrive_0_4_14.md`
- `PATCH_NOTES_CustomDrive_0_4_15.md`
- `PATCH_NOTES_CustomDrive_0_4_16.md`

Important observations from the actual `0_5_0` code state:
- the Mission 1 route -> camera -> model -> per-frame inference pipeline from the `0_4_13` to `0_4_16` line is present
- the Mission 1 object-box path is present
- the Mission 1 target-follow motor logic is present
- **Mission 1 did not yet have any web-configurable arm pose system or Mission 1 arm sequence state machine**
- `custom_drive/arm_service.py` already exists and already provides the real servo backend path for servo 0 / servo 1 / servo 2, so it was reused instead of creating a second fake arm layer

## Cause / root cause
The current Mission 1 code in the `0_5_0` baseline had no Mission 1 arm-session layer yet.

Specifically:
- there was no Mission 1 config schema for numbered 3-servo poses
- there was no Mission 1 web editor for those poses
- there was no Mission 1 mapping from named mission actions to saved pose numbers
- there was no Mission 1 state machine that applied those poses when the route started or when the target moved into the requested capture condition
- the reusable `ArmService` existed, but it did not yet expose a clean public “apply this 3-servo pose now” helper for the Mission 1 session path

So the correct forward fix was:
- extend the real `ArmService` with a direct pose-apply API
- extend Mission 1 config normalization safely
- add a Mission 1 arm sequence layer on top of the existing AI loop
- add Mission 1 web UI for pose editing + role mapping

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_1.md`

## Exact behavior changed

### 1. Mission 1 now has a numbered 3-servo pose config section
The Mission 1 config schema now includes an `arm` section with:
- `positions`
- `roles`
- `pose_settle_s`
- `grip_trigger_y_ratio`

The numbered pose store is now normalized as:
- `positions["1"]`
- `positions["2"]`
- `positions["3"]`
- etc.

Each position stores:
- `servo0`
- `servo1`
- `servo2`

This patch keeps config-safety rules:
- the existing `config/mission1_session.json` is **not** shipped in the patch zip
- new keys are added by code normalization instead of overwriting the user's runtime config file from the patch package

### 2. Mission 1 web UI now lets the user define numbered arm poses
The Mission 1 page now includes a new **Mission 1 Arm Poses** panel.

In that panel, the user can:
- edit servo 0 / servo 1 / servo 2 angles for numbered pose rows
- map those saved pose numbers to:
  - starting position
  - grip ready
  - grip
  - grip and lift
  - release
- save those settings together with the rest of the Mission 1 config

### 3. Mission 1 web UI now includes manual pose-load buttons for the mapped roles
To make the new role mappings actually usable from the web page immediately, this patch also adds manual role-load buttons:
- Load start pose
- Load grip ready
- Load grip
- Load grip and lift
- Load release

These buttons:
- save the current Mission 1 arm pose config first
- reload the real arm backend from the manual arm config
- apply the currently mapped pose for the selected role

This means the **release** mapping is not just stored — it is now testable from the Mission 1 web UI.

### 4. `ArmService` now exposes a direct pose-apply helper
`custom_drive/arm_service.py` now has new public methods:
- `set_joint_angles(...)`
- `set_pose(...)`

These methods:
- stop any active arm motion threads first
- apply direct absolute angles to servo 0 / servo 1 / servo 2
- update internal held angle state
- keep hold-refresh behavior compatible with the existing arm backend design
- return a truthful status message instead of pretending success

This was done as a forward extension of the existing arm service rather than replacing any earlier direct-servo behavior.

### 5. Mission 1 now reloads the saved starting pose when the session starts
When the Mission 1 session thread starts, it now tries to load the mapped **starting position** role before running the route.

Behavior:
- Mission 1 starts
- arm backend is reloaded from the real manual arm backend config
- Mission 1 loads the mapped starting pose
- then Mission 1 continues into the existing start-route logic

This matches the requirement:
- “load the arm starting position when start”

### 6. Mission 1 now loads grip ready when the target is first located
During the AI loop:
- once the target class is detected
- and the Mission 1 arm sequence has not yet reached grip-ready
- the mapped **grip ready** pose is loaded once

This is layered on top of the existing target-detection path and does not replace the detection table / annotated-frame pipeline.

### 7. Mission 1 now loads grip when the target is in the forward path and low enough in frame
The requested condition was:
- “when the target is in the forward path and also y < -30%. load grip.”

This patch implements that using the Mission 1 centered coordinate system already in the session app:
- forward path means `|x| < deadband`
- `y < -30%` is implemented as:
  - `target_y < -(frame_height * grip_trigger_y_ratio)`
- default `grip_trigger_y_ratio` is `0.30`

So with the default setting, grip triggers when:
- the target is centered enough to be in the forward path
- and the target center is below the frame center by more than 30% of the whole frame height

### 8. Mission 1 now loads grip and lift immediately after grip
When the above grip trigger condition is reached:
- the motors are stopped
- the mapped **grip** pose is loaded
- then the mapped **grip and lift** pose is loaded

After that:
- the Mission 1 arm sequence moves to `grip_and_lift_loaded`
- the Mission 1 follow logic holds the motors stopped instead of continuing to drive toward the target

This prevents the car from resuming target-chase motion after the capture sequence has already completed.

### 9. Mission 1 status payload now reports arm sequence state and real arm status
The Mission 1 `/api/status` payload now includes:
- `arm_sequence.state`
- `arm_sequence.last_pose_role`
- `arm_sequence.last_pose_number`
- `arm_sequence.note`
- `arm_sequence.target_lock_engaged`
- `arm_status` from the real `ArmService`

The web GUI now shows:
- arm backend enabled / available state
- arm sequence state
- mapped pose roles
- current servo 0 / servo 1 / servo 2 angles
- last arm status message

### 10. Mission 1 web viewer/status stays compatible with the accepted AI pipeline
This patch deliberately keeps the accepted Mission 1 AI/session behavior from the current line:
- route first
- then camera
- then model load
- then per-frame detection loop
- Pi-side annotated frame upload
- detection list upload
- center-origin coordinate reporting
- target-follow motor rule when the arm sequence has not yet locked the capture

No rollback was made to:
- model upload/select
- detection table
- object-box drawing
- FPS reporting
- route parsing
- Mission 1 web panel layout

## Verification actually performed
The following checks were actually performed:

1. Inspected the real `CustomDrive_0_5_0.zip` folder structure before patching instead of guessing file paths.
2. Confirmed the real CustomDrive Mission 1 entry path and files currently present in the uploaded baseline.
3. Reviewed the latest available Mission 1 patch-note history in the zip to reduce rollback risk:
   - `0_4_13`
   - `0_4_14`
   - `0_4_15`
   - `0_4_16`
4. Confirmed the current baseline does already contain:
   - `custom_drive/arm_service.py`
   - `custom_drive/mission1_session_app.py`
   - `custom_drive/mission1_web/...`
5. Extended the existing `ArmService` rather than replacing it.
6. Ran Python compile validation successfully on:
   - `custom_drive/mission1_session_app.py`
   - `custom_drive/arm_service.py`
7. Ran `node --check` successfully on:
   - `custom_drive/mission1_web/static/app.js`
8. Ran `python -m compileall .` successfully in the patched CustomDrive workspace.
9. Kept the patch package limited to changed files only, with the top-level `CustomDrive/` folder and without `__pycache__` or `.pyc` files.

## Known limits / next steps
1. This patch adds the Mission 1 arm pose system and Mission 1 arm sequence logic, but it was not hardware-tested here on the real Pi + PCA9685 + servos.
2. The actual physical meaning of each saved pose still depends on the user's real servo mounting geometry, direction, and the existing manual arm backend config.
3. The Mission 1 arm backend still reads servo wiring/backend settings from the existing manual arm config; this patch intentionally stores only the Mission 1 numbered pose values and role mapping in the Mission 1 config.
4. The `release` role is now web-configurable and manually loadable from the Mission 1 page, but this patch does **not** add a new automatic Mission 1 “release after drop-off” rule yet.
5. If a future patch is requested, the next useful follow-up would be:
   - a release/drop-off trigger rule
   - pose interpolation or timed transitions
   - separate settle times for grip vs lift vs release
