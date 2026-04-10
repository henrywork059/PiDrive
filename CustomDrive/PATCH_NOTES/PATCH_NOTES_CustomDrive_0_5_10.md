# PATCH NOTES — CustomDrive_0_5_10

## Request summary
Patch the current CustomDrive Mission 1 line so that:

1. the **status overlay on the frame** updates live and clearly shows the mission/runtime state
2. Mission 1 status clearly shows both the **state of the car** and its **intended motion**
3. when the car reaches the **grip zone**, it **stops moving first** before running the arm pose sequence
4. motion handling is divided into **cleaner explicit states** instead of one inline transition block

The user explicitly asked for this as a forward patch on the current CustomDrive line and asked that the implementation be careful and concrete.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive line represented in the workspace by:
- uploaded `CustomDrive_0_5_0.zip` baseline
- accepted Mission 1 patches through `0_5_9`

Before patching, the recent patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_6.md`
- `PATCH_NOTES_CustomDrive_0_5_7.md`
- `PATCH_NOTES_CustomDrive_0_5_8.md`
- `PATCH_NOTES_CustomDrive_0_5_9.md`

Accepted behavior intentionally preserved:
- typed start route syntax and order
- route -> camera -> model -> AI-loop pipeline
- class 1/2 pickup + class 3/4 drop-off mission loop
- single-box viewer behavior from `0_5_9`
- separate tracking-x vs capture-x gate behavior from `0_5_9`
- current arm pose numbering / role mapping
- real `ArmService` backend
- Mission 1 motor logic from `0_5_6` and `0_5_5`

## Cause / root cause found
The current Mission 1 code had three real issues related to the user’s request.

### 1. Frame overlay status was too limited
The Pi-annotated frame only showed a small footer line with:
- FPS
- mission state
- held class
- drop-off class
- model name

It did **not** show the current intended motion, and it did not clearly expose the clean mission step the car was currently executing.

### 2. Mission 1 status exposed `car_turn_direction` but not a cleaner high-level movement intent
The current status payload and web UI showed `car_turn_direction`, but that is only the immediate direction label. It did not show a cleaner high-level movement intention such as:
- `search_rotate_clockwise`
- `approach_forward`
- `turn_left_to_target`
- `hold_stop`
- `grip_pose`
- `grip_and_lift_pose`
- `release_pose`

So the runtime state was still understandable only by reading several fields together.

### 3. Grip / release transitions stopped the motors, but not as their own clean motion state
Before this patch, the close-enough branch already called `_stop_with_note(...)` before the grip/release poses. So the car was technically told to stop.

However, that stop was still an **inline transition** inside the same branch:
- no dedicated stop-before-grip state
- no dedicated stop-before-release state
- no explicit short stop/settle pause before the arm moved
- no clearer motion-intent reporting for these transitions

That made the motion flow harder to reason about and harder to debug from the live UI.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_10.md`

## Exact behavior changed

### 1. Mission 1 now tracks an explicit `intended_motion` field
A new live state field was added:
- `intended_motion`

This now reports the high-level movement/action intention separately from `car_turn_direction`.

Examples now used by Mission 1:
- `idle`
- `queued`
- `route_forward`
- `route_backward`
- `route_turn_left`
- `route_turn_right`
- `camera_boot`
- `model_boot`
- `wait_for_frame`
- `search_rotate_clockwise`
- `approach_forward`
- `turn_left_to_target`
- `turn_right_to_target`
- `hold_stop`
- `grip_pose`
- `grip_and_lift_pose`
- `release_pose`
- `reverse_reset`
- `stopped`

This field is now included in:
- Mission 1 backend status payload
- web summary cards
- web status panel
- viewer stat pills
- Pi-side annotated frame overlay

### 2. Pi-annotated frame now includes a live mission-status overlay panel
The Pi-generated frame overlay was upgraded from a small footer line into a larger live status panel drawn onto the frame.

It now shows live:
- `phase`
- `mission_state`
- `intended_motion`
- `car_turn_direction`
- `target_side`
- held class
- drop-off class
- arm stage
- loaded model
- pipeline FPS
- target centre coordinates when available
- current command note

Because this panel is rendered into the Pi JPEG every AI cycle, it updates live with the mission state while the frame is running.

### 3. Mission 1 now has an explicit stop-before-pose transition helper
A new helper was added so the car cleanly enters a stop state before arm actions:
- `_stop_for_pose_transition(...)`

This helper now:
- sets explicit mission/current phase state
- sets `intended_motion = hold_stop`
- sets `car_turn_direction = stopped`
- sets `target_side = center`
- sends the stop motor command
- applies a short settle delay before the arm pose runs

### 4. Pickup grip zone now uses clean separated motion states
When a pickup target reaches the grip zone, Mission 1 now goes through explicit stages instead of one inline block:

1. `pickup_stop_for_grip`
2. `pickup_grip`
3. `pickup_lift`
4. `dropoff_search`

And the motion intent reflects those stages:
- `hold_stop`
- `grip_pose`
- `grip_and_lift_pose`
- then `search_rotate_clockwise`

This makes the stop-before-grip behavior explicit and easier to debug.

### 5. Drop-off release now uses clean separated motion states
When a drop-off target reaches the release zone, Mission 1 now goes through explicit stages:

1. `dropoff_stop_for_release`
2. `dropoff_release`
3. `reverse_reset`
4. `pickup_search`

And the motion intent reflects those stages:
- `hold_stop`
- `release_pose`
- `reverse_reset`
- `search_rotate_clockwise`

### 6. Added a dedicated short stop/settle time before grip and release
A new Mission 1 arm config key is normalized in code:
- `arm.motion_stop_settle_s`

Default:
- `0.2`

This gives the car a brief stop/settle period before the arm grip/release pose sequence starts.

This key is normalized in code for safe persistence, but it is **not yet exposed in the web UI** in this patch.

### 7. Camera/model boot now also expose cleaner intended motion
The backend now marks these phases explicitly:
- camera start phase -> `camera_boot`
- model load phase -> `model_boot`

So the live status now reads more truthfully during startup, not only during target tracking.

### 8. Mission 1 web UI now shows the intended motion explicitly
The web viewer and status panels were updated so Mission 1 now shows both:
- current mission state
- intended motion

This was added to:
- summary cards
- status grid
- viewer stat pills
- viewer note text

The viewer subtitle was also corrected so it now describes the current real behavior:
- Pi frame with Pi-side labels
- live mission-status overlay burned into the frame
- light web guide overlay only

## Verification actually performed
The following checks were actually run:

1. Reconstructed the current CustomDrive Mission 1 workspace from the available baseline plus accepted Mission 1 patch line through `0_5_9`.
2. Reviewed the recent Mission 1 patch notes `0_5_6` through `0_5_9` before editing.
3. Inspected the real current Mission 1 state/motion code and confirmed:
   - status payload did not expose a clean high-level intended motion field
   - frame annotation did not show enough live mission state information
   - grip/release transitions stopped inline but did not have separate stop-before-pose state handling
4. Patched the Mission 1 backend to:
   - add `intended_motion`
   - add `_stop_for_pose_transition(...)`
   - add explicit stop/grip/lift/release state transitions
   - add live frame overlay lines
   - normalize `arm.motion_stop_settle_s`
5. Patched the Mission 1 frontend to:
   - show intended motion in the status grid
   - show intended motion in summary cards
   - show intended motion in viewer stat pills and note text
   - update the viewer subtitle to match the real overlay behavior
6. Ran:
   - `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`
   - `node --check CustomDrive/custom_drive/mission1_web/static/app.js`
   - `python -m compileall CustomDrive/custom_drive`
7. Checked that the patch zip contains only changed/new files plus patch notes, with the top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. This patch adds a code-level stop/settle pause before grip/release, but it does not redesign the actual arm pose angles.
   - if the arm still reaches the wrong physical posture, the next grounded check is still the saved pose angles and servo directions

2. `arm.motion_stop_settle_s` is normalized in config, but it is not yet exposed as a web input.
   - if wanted, the next patch can add a small Mission 1 UI field for that stop-before-pose settle time

3. The new live frame overlay uses short text lines to avoid clutter.
   - if you want a more styled HUD later, that should be a separate UI polish patch

4. This patch makes the motion states cleaner around grip and release.
   - it does not redesign the higher-level pickup/drop-off mission logic beyond those state transitions
