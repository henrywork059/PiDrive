# PATCH NOTES — CustomDrive_0_5_9

## Request summary
Patch the current CustomDrive Mission 1 line to fix two issues:

1. The mission was entering the detection loop and loading **Grip ready**, but it was not reliably progressing into **Grip** and **Grip and lift**.
2. The web viewer was showing **two boxes** around detected objects because the Pi frame was already annotated and the browser overlay was drawing another box set on top.

The user also explicitly asked that the arm-control / posture logic be checked against the older accepted arm code and that the fix be delivered as a forward patch without rolling back the current Mission 1 pipeline.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive Mission 1 line represented in the workspace by:
- repo CustomDrive baseline
- accepted Mission 1 patches through `0_5_8`

Before patching, the recent patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_5.md`
- `PATCH_NOTES_CustomDrive_0_5_6.md`
- `PATCH_NOTES_CustomDrive_0_5_7.md`
- `PATCH_NOTES_CustomDrive_0_5_8.md`

Accepted behavior intentionally preserved:
- typed start route format and order
- route -> camera -> model -> detection-loop Mission 1 pipeline
- pickup / drop-off class loop
- saved arm-pose numbering and role mapping
- arm backend remains the real `ArmService`
- Pi-side annotated frame generation remains intact
- detection list, centered coordinates, FPS reporting, and mission-state reporting remain intact
- reduced **tracking** x deadband from `0_5_4` remains intact for steering behavior

## Cause / root cause found
Two real code-level problems were found.

### 1. Grip / release gating was using the same x deadband that had been globally reduced earlier
Mission 1 was using `drive.target_x_deadband_ratio` for two different jobs:

1. **tracking / steering decision**
   - whether the car should drive forward or keep turning toward the target
2. **capture / release gate**
   - whether the target is centered enough to trigger the arm sequence

Earlier accepted patch `0_5_4` reduced that x range by 30%.
That was valid for the live steering window, but it also unintentionally made the **grip / release gate** more strict.

So the current code could do this:
- detect pickup target
- load **Grip ready**
- keep tracking target
- never satisfy the stricter capture gate
- therefore never reach **Grip** / **Grip and lift**

This matched the current runtime behavior seen in the user-provided log: Mission 1 reached **Grip ready** after detection started, but no later grip-stage log appeared in the same run.

### 2. The browser overlay was intentionally drawing a second box set on top of the Pi-annotated frame
The current Mission 1 viewer was doing both of these at the same time:

1. the Pi backend annotated the JPEG frame with boxes and labels
2. the browser overlay drew another set of SVG boxes from the same detection list

That made the viewer show duplicate boxes around the same object.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_9.md`

## Exact behavior changed

### 1. Tracking x-deadband and arm capture x-deadband are now separated
A new Mission 1 arm config key was added:
- `arm.capture_x_tolerance_ratio`

Default:
- `0.05`

Behavior now:
- **tracking / steering** still uses `drive.target_x_deadband_ratio`
  - this preserves the accepted tighter steering window from `0_5_4`
- **pickup / release gate** now uses `arm.capture_x_tolerance_ratio`
  - default `5%` of frame width

This means Mission 1 can keep the tighter steering feel while still using the intended wider capture/release gate for the arm sequence.

### 2. Pickup and drop-off close-enough checks now use the dedicated capture window
The helper that decides whether a target is close enough was changed so it now uses:
- x gate: `arm.capture_x_tolerance_ratio`
- y gate: `arm.grip_trigger_y_ratio`

This applies to both:
- pickup -> Grip / Grip and lift
- drop-off -> Release

So the grip trigger is no longer unintentionally tightened by the earlier x-range reduction patch.

### 3. Mission 1 now emits throttled gate-debug events during pickup and drop-off tracking
To make future debugging much easier, Mission 1 now logs throttled gate-check events while it is tracking but has not yet triggered the arm step.

These events include:
- target centered x
- target centered y
- tracking deadband in px
- capture deadband in px
- grip-trigger y threshold in px
- whether `close_enough` is currently true

This gives future debugging a truthful record of why the arm did or did not trigger.

### 4. Duplicate browser box drawing was removed
The Mission 1 browser overlay no longer draws its own duplicate SVG detection boxes.

The viewer now shows:
- the **Pi-generated annotated frame** with its real boxes and labels
- a light guide overlay only
  - center lines
  - center band
  - target center dot for the active target when present

This removes the duplicate box problem while still keeping the helpful alignment guides.

### 5. Viewer note text now matches the real behavior
The viewer note was updated so it no longer claims the browser is drawing another box set.
It now correctly states that the page is showing the Pi-generated annotated frame with a light guide overlay only.

## Verification actually performed
The following checks were actually run:

1. Reconstructed the current CustomDrive Mission 1 workspace from the available repo baseline plus accepted patch line through `0_5_8`.
2. Reviewed recent patch notes `0_5_5` through `0_5_8` before editing to reduce rollback risk.
3. Inspected the real Mission 1 backend and confirmed:
   - grip / release gating still used `drive.target_x_deadband_ratio`
   - the browser overlay intentionally drew a second box layer on top of the Pi-annotated frame
4. Patched the Mission 1 backend so:
   - tracking deadband and capture deadband are separated
   - pickup and drop-off gate checks use the new capture deadband
   - throttled pickup/drop-off gate logs are emitted
5. Patched the Mission 1 frontend so the overlay no longer draws duplicate boxes.
6. Ran:
   - `python -m py_compile custom_drive/mission1_session_app.py custom_drive/arm_service.py custom_drive/manual_control_config.py`
   - `node --check custom_drive/mission1_web/static/app.js`
   - `python -m compileall custom_drive`
7. Checked the patch zip structure to ensure it is patch-only with the correct top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. This patch removes the code-level duplicate-box behavior and restores a wider arm trigger gate, but it does not retune the actual saved arm angles.
   - if the arm still reaches the wrong physical posture, the next thing to inspect is the saved Mission 1 pose values themselves
2. The new capture-x tolerance is normalized in code, but it is not yet exposed as a dedicated Mission 1 web control.
   - if desired, the next patch can add a small Mission 1 web field for `capture_x_tolerance_ratio`
3. The gate-debug events are throttled to avoid log spam.
   - they are meant for truthful debugging, not for every single frame
4. This patch does not change the accepted pickup/drop-off state machine ordering.
   - it only makes the grip / release gate less brittle and makes the viewer reflect the real single-box pipeline
