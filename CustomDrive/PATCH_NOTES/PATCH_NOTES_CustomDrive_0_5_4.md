# PATCH NOTES — CustomDrive_0_5_4

## Request summary
Reduce the Mission 1 x range by 30%.

In the current Mission 1 logic, the x range is the center deadband used for:
- deciding whether the target is considered centered enough to drive forward
- deciding whether the target is left / center / right
- deciding whether the pickup / drop-off close-enough x condition is satisfied
- drawing the visible center band in the annotated frame and web overlay

The requested change was to make that x range 30% smaller.

## Baseline / rollback review
This patch was built forward from the latest accepted Mission 1 patch line available in the container:
- `CustomDrive_0_5_3.zip`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_1.md`
- `PATCH_NOTES_CustomDrive_0_5_2.md`
- `PATCH_NOTES_CustomDrive_0_5_3.md`

Accepted Mission 1 behavior intentionally preserved:
- start route still runs before camera/model startup
- pickup search / drop-off search state machine remains in place
- box drawing / detection list / FPS reporting remain unchanged
- arm pose logic and grip / lift / release sequence remain unchanged
- post-pickup immediate drop-off search handoff from `0_5_3` remains unchanged

## Cause / root cause
The current Mission 1 center x deadband was still using the previous full width configured in `drive.target_x_deadband_ratio`.

That ratio is used by multiple linked Mission 1 behaviors, so changing only one branch would have created mismatch between:
- tracking logic
- close-enough logic
- target-side reporting
- center-band drawing

The safe forward fix was to reduce the normalized Mission 1 `target_x_deadband_ratio` by 30% in one place and keep the rest of the pipeline reading that same normalized value.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_4.md`

## Exact behavior changed

### 1. Mission 1 target x deadband is now 30% smaller
The effective Mission 1 `target_x_deadband_ratio` is now reduced to 70% of its previous value.

Examples:
- previous default `0.050` -> new effective default `0.035`
- existing saved value `0.100` -> new effective value `0.070`

This directly reduces the width of the center x range by 30%.

### 2. The reduction is applied consistently across Mission 1
Because the same normalized value is reused everywhere, the 30% reduction now affects all linked Mission 1 behaviors consistently:
- forward-vs-turn decision
- pickup close-enough x condition
- drop-off close-enough x condition
- target side labeling
- center-band drawing in the annotated frame
- center-band drawing in the web overlay

### 3. Existing saved Mission 1 configs are migrated once
A one-time Mission 1 config migration marker was added:
- `drive._target_x_deadband_migration_v`

Behavior:
- if the saved Mission 1 config has not yet had this deadband reduction applied, the code reduces the saved deadband by 30% at load time
- once saved again, the reduced value and migration marker are persisted
- future loads do not keep shrinking the value repeatedly

This avoids the bug of reducing the x range every time the app starts.

### 4. New default also matches the reduced range
The Mission 1 built-in default was changed from `0.05` to `0.035` so new configs start with the reduced x range too.

## Verification actually performed
The following checks were actually performed in the patch workspace:

1. Opened the actual latest Mission 1 backend and traced where `target_x_deadband_ratio` is used.
2. Confirmed it feeds both control logic and center-band drawing.
3. Patched the normalization path so the reduction is applied consistently in one place.
4. Added a one-time migration flag so existing configs do not shrink repeatedly.
5. Ran `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`.
6. Ran `python -m compileall CustomDrive`.
7. Checked the patch zip structure to ensure it contains only changed files plus patch notes, with a top-level `CustomDrive/` folder and no cache files.

## Known limits / next steps
- This patch changes the Mission 1 x deadband only. It does not change the y grip trigger threshold.
- If you later want the x range adjusted again, the cleanest path is to either:
  - edit the value directly in Mission 1 settings, or
  - add a clearly labeled “effective x deadband preset” control in the web UI.
- The migration marker is Mission 1 specific and only affects `target_x_deadband_ratio`.
