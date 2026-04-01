# CustomDrive 0_3_4 Patch Notes

## Request summary
Fix the current CustomDrive arm control because it still feels off, while keeping the accepted AI/backend changes from `0_3_1` to `0_3_3` intact.

The goal of this patch is to make the arm control path correct and robust again from:
- GUI button hold behavior
- action routing
- configurable lift / gripper direction handling
- arm status/error reporting

## Anti-rollback review performed
Before patching, I re-read the latest accepted CustomDrive notes relevant to the current state and the arm path:
- `0_3_3`
- `0_3_2`
- `0_3_1`
- `0_2_9`
- `0_2_8`
- `0_2_7`

That review was used to avoid rolling back:
- the recent AI backend/debug changes
- the 2x arm speed behavior
- the press-and-hold arm model
- the lift hold-on-stop behavior
- the dedicated gripper-on-servo-2 behavior

## Root cause
There were three practical issues.

### 1) The GUI hold binding had drifted away from the earlier pointer-capture direction
The current browser hold binding stopped motion on `pointerleave` and did not actively keep pointer capture through the hold.

That means a small finger / mouse drift outside the button can stop arm motion early even though the user is still holding the control.

That matches the earlier arm-control requirement history badly and is exactly the kind of behavior that makes the arm feel unreliable or "off."

### 2) Lift/gripper direction assumptions were still hardcoded in code
The current backend still assumed:
- `Up` always means negative lift angle movement
- `Open` always means negative gripper angle movement

That preserved one earlier linkage assumption, but it did not provide a safe forward way to correct direction if the real hardware linkage is reversed.

### 3) Successful stop operations could still leave an old arm error visible
`stop_motion()` and `stop_grip_motion()` could finish successfully but leave a stale `last_error` string from an earlier failure.

That can make the UI look like the arm is still in a bad/error state even when the latest stop/hold action actually succeeded.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_4.md`

## Exact behavior changed

### 1) Arm hold buttons now keep control more reliably
The GUI arm buttons now use pointer capture during the hold lifecycle.

That means:
- press starts the action
- release / cancel / lost capture stops the action
- simple pointer drift outside the button no longer stops the arm early just because the cursor/finger moved slightly

This restores the earlier intended hold behavior more reliably for both mouse and touch-style usage.

### 2) Lift direction is now explicitly configurable
A new arm config key is supported:
- `lift_up_direction`

Allowed effective values are:
- `-1` = `Up` reduces lift angle, `Down` increases lift angle
- `1` = `Up` increases lift angle, `Down` reduces lift angle

Default remains `-1`, so current behavior is preserved unless the hardware linkage needs to be flipped.

### 3) Gripper direction is now explicitly configurable
A new arm config key is supported:
- `grip_open_direction`

Allowed effective values are:
- `-1` = `Open` reduces gripper angle, `Close` increases gripper angle
- `1` = `Open` increases gripper angle, `Close` reduces gripper angle

Default remains `-1`, so current behavior is preserved unless the physical gripper linkage is reversed.

### 4) Arm status now reports the active direction settings
The arm status payload now includes:
- `lift_up_direction`
- `grip_open_direction`

That makes it easier to confirm which direction logic is currently active instead of guessing from the code.

### 5) Successful stop actions now clear stale errors
When lift/gripper stop-and-hold succeeds, the backend now clears old `last_error` state.

This prevents the GUI warning banner from continuing to show an outdated arm error after a successful hold/stop action.

### 6) No config wipe / no rollback of the 2x speed update
This patch does **not** replace the user's `manual_control.json`.

It keeps:
- the 2x arm speed behavior from `0_3_1`
- lift on channels 0 + 1
- gripper on channel 2
- lift hold-on-stop
- dedicated stop routes for lift vs gripper

### 7) GUI asset version bumped forward
The GUI asset version was updated to `0_3_4` so the browser is more likely to fetch the updated JavaScript immediately.

## Verification actually performed
- Reconstructed the active CustomDrive code state forward from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
  - `CustomDrive_0_3_3_patch.zip`
- Re-read the recent patch notes listed above before editing.
- Inspected the real arm path end-to-end in:
  - `arm_service.py`
  - `manual_control_config.py`
  - `gui_control_app.py`
  - `gui_web/static/app.js`
- Ran Python syntax checks on the changed Python files.
- Ran JavaScript syntax check on `gui_web/static/app.js`.
- Ran `python -m compileall custom_drive`.
- Ran small code-level checks confirming:
  - default arm direction settings remain `-1`
  - configurable direction overrides are accepted
  - successful stop operations now clear stale `last_error`

## Known limits / next steps
- I did **not** claim live Pi hardware validation in this container.
- This patch makes the arm control path more correct and configurable, but final physical "correct direction" still depends on the real linkage.
- If your hardware moves opposite to the intended button labels after this patch, set these in `CustomDrive/config/manual_control.json` under `arm`:
  - `"lift_up_direction": 1`
  - `"grip_open_direction": 1`
  and restart the GUI.
- I intentionally did **not** overwrite your config file in the patch zip, to avoid wiping any local working values.
