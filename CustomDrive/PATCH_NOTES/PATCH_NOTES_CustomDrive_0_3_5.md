# CustomDrive 0_3_5 Patch Notes

## Request summary
Fix the current CustomDrive arm path because the arm servo seems to release by itself sometimes.

This patch was made forward on top of the current accepted CustomDrive state, keeping the recent AI/backend fixes and the recent arm-control fixes intact.

## Anti-rollback review performed
Before patching, I checked:
- the current reconstructed code state built from `CustomDrive_0_3_0` plus accepted `0_3_1` to `0_3_4`
- the latest patch note: `0_3_4`
- the previous three recent notes: `0_3_3`, `0_3_2`, `0_3_1`
- the earlier arm-specific notes: `0_2_7`, `0_2_8`, `0_2_9`

That review was used to avoid rolling back:
- the GUI direction already accepted
- the press-and-hold lift / gripper model
- the dedicated lift-vs-gripper stop actions
- the lift/gripper direction config keys
- the 2x arm speed behavior
- the startup and stop-time hold reassert behavior
- the recent AI backend/debug fixes

## Root cause
The earlier lift fix in `0_2_9` correctly reasserted hold on startup and on stop, but the current service still had two backend weaknesses that could allow an intermittent "released by itself" feeling later.

### 1) ServoKit writes were not serialized across the lift and gripper worker threads
The arm service runs separate worker threads for:
- lift motion
- gripper motion

Both threads ultimately talk to the same PCA9685 / ServoKit backend, but the actual servo writes were not protected by one shared I/O lock.

That means overlapping writes could happen on the shared backend, especially when the lift and gripper are both being used in the same session. On real hardware, that kind of shared-bus race can show up as flaky or intermittent holding behavior.

### 2) Hold was only explicitly reasserted at startup and stop time
If the PCA9685 / servo signal momentarily drooped later, or the arm linkage relaxed after being idle for a while, there was no periodic backend keepalive to reassert the current hold angles.

So the service had good startup/stop holding behavior, but not a persistent idle-time hold refresher.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_5.md`

## Exact behavior changed

### 1) All ServoKit writes are now serialized through one shared arm I/O lock
The actual `servo[channel].angle = ...` writes now run through a shared re-entrant lock.

This means lift, gripper, startup hold, stop hold, and keepalive hold refreshes no longer write to the PCA9685 backend at the same time from competing threads.

### 2) Idle-time hold refresh is now supported and enabled by default
The arm service now starts a lightweight background hold-refresh thread when the PCA9685 backend comes up successfully.

While the arm is idle, that thread periodically reapplies:
- the current lift hold angle
- the current gripper hold angle

This is meant to reduce the chance that the arm appears to "let go" after sitting still for a while.

### 3) Hold refresh pauses automatically while the arm is actively moving
The keepalive does **not** fight the motion threads.

If lift or gripper motion is currently active, the refresh thread skips that cycle and waits for the arm to become idle again before reasserting hold.

### 4) Hold-refresh behavior is now configurable without wiping the user's config
Two new backward-compatible arm config keys are now supported:
- `hold_refresh_enabled` (default `true`)
- `hold_refresh_interval_s` (default `0.75`)

Existing configs do not need to be replaced. Missing keys are filled safely in code.

### 5) Arm status now exposes hold-refresh state
The arm status payload now includes:
- `hold_refresh_enabled`
- `hold_refresh_interval_s`
- `hold_refresh_running`

This makes it easier to confirm from the GUI/backend status whether the keepalive path is active.

### 6) No change to the accepted user-facing arm controls
This patch does **not** change:
- Up / Down button meanings
- Open / Close button meanings
- the current configurable direction settings
- the 2x arm speed change
- the current press-and-hold UI behavior

## Verification actually performed
- Reconstructed the working CustomDrive state forward from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
  - `CustomDrive_0_3_3_patch.zip`
  - `CustomDrive_0_3_4_patch.zip`
- Re-read the relevant patch notes listed above before editing.
- Ran Python syntax checks on:
  - `custom_drive/arm_service.py`
  - `custom_drive/manual_control_config.py`
- Ran:
  - `python -m compileall custom_drive`
- Ran a small code-level smoke test with a fake ServoKit-style object to verify that:
  - hold refresh starts successfully
  - the refresh thread periodically reapplies lift and gripper angles
  - the refresh thread stops cleanly
  - status reports `hold_refresh_running` correctly

## Known limits / next steps
- I did **not** claim live hardware validation in this container.
- If the servo still appears to release after this patch, the next thing to check is power and physical load, because software can reassert angles but cannot fully compensate for brownout / insufficient servo power.
- If you want to tune the keepalive cadence, set under `arm` in `CustomDrive/config/manual_control.json`:
  - `"hold_refresh_enabled": true`
  - `"hold_refresh_interval_s": 0.5`
  and restart the GUI.
- I intentionally did **not** overwrite your local config file in the patch zip.
