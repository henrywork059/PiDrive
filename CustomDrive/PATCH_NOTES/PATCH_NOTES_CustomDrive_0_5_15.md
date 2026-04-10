# PATCH NOTES — CustomDrive_0_5_15

## Request summary
Patch the current CustomDrive Mission 1 line so that:

1. the Mission 1 web display does not appear frozen when the pickup target reaches the grip trigger Y threshold and the arm pose sequence begins
2. the **Grip trigger Y** setting from the web panel actually applies in a way that matches the user's intended percentage-based workflow
3. **Pose settle (s)** is visibly applied between each Mission 1 pose stage without making the UI/frame look stuck
4. the legacy **target class ID** control is removed from the Mission 1 page because Mission 1 now always searches pickup classes **1 and 2** automatically

Additional user clarification captured in this patch:
- the user is testing Mission 1 logic in a non-Pi environment at times, so the patch must improve UI/logic behavior without depending on real hardware movement
- the user specifically described the issue as the web display freezing when the grip trigger is reached and only unfreezing after the grip logic finishes

## Baseline / rollback review
This patch was built forward from the reconstructed current CustomDrive Mission 1 workspace represented by:
- the accessible repo CustomDrive baseline in the workspace
- accepted Mission 1 patch zips through `0_5_14`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_11.md`
- `PATCH_NOTES_CustomDrive_0_5_12.md`
- `PATCH_NOTES_CustomDrive_0_5_13.md`
- `PATCH_NOTES_CustomDrive_0_5_14.md`

Accepted behavior intentionally preserved:
- route -> camera -> model -> AI loop startup order
- Mission 1 pickup / drop-off state machine and class mapping
- current Arm Position and Motor Status panels
- current turn-logic and hardware-output motor calibration controls
- current Pi-side annotated frame overlay and web guide overlay
- current stop-before-grip / stop-before-release flow

## Cause / root cause found
There were three real issues in the current `0_5_14` Mission 1 line.

### 1. Pose-settle sleeps blocked visible frame/overlay updates during grip and release staging
The backend already split Mission 1 into cleaner states such as:
- `pickup_stop_for_grip`
- `pickup_grip`
- `pickup_lift`
- `dropoff_stop_for_release`
- `dropoff_release`

However, those stages still used direct `time.sleep(...)` calls inside the Mission 1 detection-loop thread for:
- motion-stop settle
- grip pose settle
- grip-and-lift pose settle
- release pose settle

Because the annotated JPEG was only refreshed when the detection-loop iteration finished, the web viewer could appear frozen at the moment the car entered the grip/release pose sequence, even though the backend state had already changed.

### 2. Grip trigger Y input was still treated like a raw fraction in the UI
The Mission 1 arm config stores `grip_trigger_y_ratio` internally as a fraction like:
- `0.30` for 30%

But the user's workflow and mission wording naturally treat that field as a percentage threshold such as:
- `30` for 30%

So when the user changed the input box expecting percentage behavior, the value could feel like it was not applying as intended.

### 3. Legacy target class ID control was stale
Mission 1 no longer uses a single manually selected pickup class. The current mission logic already auto-searches:
- pickup classes `1` and `2`
- then drop-off class `3` or `4` based on what is being held

So the old **Legacy target class ID** field on the page was stale and misleading.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_15.md`

## Exact behavior changed

### 1. Mission 1 pose-settle waits now keep the annotated frame/overlay alive
A new backend helper was added so Mission 1 pose-timing waits can refresh the annotated frame during:
- stop-before-grip settle
- grip pose settle
- grip-and-lift settle
- stop-before-release settle
- release pose settle

This keeps the frame overlay and status text visibly alive while the Mission 1 state machine is waiting between pose stages.

### 2. Pose settle still applies between each pose, but no longer looks like a dead UI pause
Mission 1 still waits for the configured settle timing, but the wait now happens with live frame refresh support.

That means the Mission 1 viewer can continue to show the current stage and intended motion while the backend is waiting between pose stages.

### 3. Grip trigger Y input is now percentage-based in the web UI
The Mission 1 page now shows:
- **Grip trigger Y (%)**

The web UI now:
- displays the stored config as a percentage value
- saves the entered value back to the backend as a fraction

Examples:
- entering `30` in the box saves `0.30`
- entering `45` in the box saves `0.45`

### 4. Backend normalization now also accepts percent-style values defensively
Mission 1 config normalization now accepts either:
- a fraction (`0.30`)
- or a percentage-style number (`30`)

If the incoming value is greater than `1.0`, it is treated as a percentage and divided by `100` before clamping.

This protects against mixed older/newer UI saves and manual JSON edits.

### 5. Legacy target class ID field was removed from the Mission 1 page
The stale Mission 1 setup field for **Legacy target class ID** was removed from the web template and web config collection code.

Mission 1 now presents the actual current behavior more clearly:
- pickup search always looks for classes `1` and `2`
- drop-off search follows the held-class mapping

### 6. Current mission logic remains unchanged with respect to pickup/drop-off targeting
This patch does **not** change the underlying pickup/drop-off targeting rules.
It only removes the stale page control that no longer matched the real mission logic.

## Verification actually performed
The following checks were actually performed in the patched workspace:

1. Reconstructed the current CustomDrive Mission 1 workspace from the accessible repo baseline plus accepted Mission 1 patches through `0_5_14`.
2. Reviewed the recent Mission 1 patch-note history `0_5_11` through `0_5_14` before editing.
3. Inspected the current Mission 1 backend and confirmed the grip/release stage waits were still using direct blocking sleeps inside the detection-loop thread.
4. Patched the backend so pose-settle / stop-settle waits refresh the live annotated frame during those waits.
5. Updated the Mission 1 web UI so **Grip trigger Y** is displayed and collected as a percentage.
6. Added defensive backend normalization so either fraction or percent-style values are accepted for `grip_trigger_y_ratio`.
7. Removed the stale **Legacy target class ID** field from the Mission 1 page and web config collection path.
8. Ran `python -m py_compile` on the changed Python files.
9. Ran `python -m compileall` on the patched `custom_drive` package.
10. Ran `node --check` on the patched Mission 1 `app.js`.
11. Verified the patch zip structure is patch-only with the correct top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
1. This patch keeps the existing threaded Flask runtime and Mission 1 detection loop architecture. The pose stages are still sequential in the backend; this patch focuses on keeping the UI/frame visibly alive during those waits rather than converting the whole pose flow into a fully asynchronous action queue.
2. The backend still keeps the legacy `session.target_class_id` config key internally for backward compatibility, even though the web page no longer exposes it.
3. The current Mission 1 page now treats **Grip trigger Y** as a percent input. If future tuning fields also feel more natural in percent form, the same conversion approach can be applied to those controls too.
