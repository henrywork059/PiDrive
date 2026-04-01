# CustomDrive 0_3_9 Patch Notes

## Request summary
Patch the current CustomDrive state so that:
- the arm control no longer uses the old Up / Down lift control,
- servo 0 and servo 1 can be controlled directly and independently,
- the four direct-servo buttons are arranged in a square,
- the Open / Close buttons remain but are shorter,
- the AI settings page gets a Stop AI button to stop the current deployment,
- and the patch must be checked against the previous accepted fixes so the same earlier arm mistakes are not repeated.

## Anti-rollback review performed
Before patching, I checked:
- the reconstructed current code state built from `CustomDrive_0_3_0` plus accepted `0_3_1` to `0_3_8`
- the latest patch note: `0_3_8`
- the previous three recent notes: `0_3_7`, `0_3_6`, `0_3_5`
- the earlier arm-specific notes used to avoid regressions: `0_3_4`, `0_2_9`, `0_2_8`, `0_2_7`

That review was used to avoid rolling back:
- pointer-capture hold behavior for press-and-hold arm buttons
- startup hold / stop-time hold behavior
- serialized ServoKit / PCA9685 writes
- hold refresh keepalive behavior
- gripper isolation on servo 2
- 2x arm speed behavior
- the cleaned AI settings layout and real overlay cadence control
- the working AI deploy/debug path

## Root cause / design issue
The current arm implementation still treated servo 0 and servo 1 as one linked “lift” axis internally.
That no longer matched the requested workflow.

The current UI and backend still assumed:
- one grouped lift motion path (Up / Down)
- one gripper path (Open / Close)

So even though earlier patches fixed reliability problems, the arm model itself was still the older grouped-lift design.

On the AI side, the settings page had no clean way to stop a deployment without deleting model files or manually changing config state.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_9.md`

## Exact behavior changed

### 1) Servo 0 and servo 1 are now direct independent hold-to-move controls
The arm backend now supports:
- `start_servo0_positive` / `stop_servo0`
- `start_servo0_negative` / `stop_servo0`
- `start_servo1_positive` / `stop_servo1`
- `start_servo1_negative` / `stop_servo1`

Each servo now keeps its own:
- motion thread
- stop event
- live angle state

This means servo 0 and servo 1 are no longer forced to move as one linked lift axis when using the new GUI controls.

### 2) The previous arm safety fixes were kept instead of being replaced
The direct-servo rewrite keeps the important accepted protections from earlier patches:
- shared PCA9685 / ServoKit write lock
- idle hold refresh thread
- stop-and-hold behavior after a button release
- startup hold reassertion
- press-and-hold button model
- gripper still isolated on servo 2
- current speed multiplier behavior

So this patch changes the arm control model without throwing away the earlier reliability fixes.

### 3) The GUI arm panel now shows four direct-servo buttons in a square
The old Up / Down buttons were removed from the current GUI page.
They were replaced with:
- Servo 0 +
- Servo 1 +
- Servo 0 -
- Servo 1 -

These are arranged as a 2x2 square and each uses the existing press-and-hold interaction model.

### 4) Open / Close remain for servo 2, but are shorter
The Open / Close controls were kept for the gripper on servo 2.
Their height was reduced so the arm panel better matches the new direct-servo layout.

### 5) Arm status now reports servo 0 and servo 1 angles directly
The arm status payload now includes:
- `servo0_angle`
- `servo1_angle`
- `servo0_channel`
- `servo1_channel`
- `servo0_moving`
- `servo1_moving`
- `direct_servo_control`

The top status card now shows `Arm 0 / 1` instead of only the old single lift angle.

### 6) Legacy grouped lift actions are still accepted for compatibility
To avoid breaking any older callers unexpectedly, the backend still accepts the old grouped lift actions:
- `start_up`
- `start_down`
- `stop_lift`

These now proxy to both direct servo channels together.
The current GUI no longer uses them, but they were left in place as a compatibility layer.

### 7) AI settings now have a real Stop AI action
A new backend undeploy path was added.
The new Stop AI button:
- stops the active AI deployment
- clears the live deployed interpreter state
- preserves uploaded model files
- preserves the rest of the AI settings
- updates the saved config so `deployed_model` becomes `none`
- turns off the active deployment cleanly instead of forcing a file delete

This is intentionally different from Delete Model.
Delete removes files.
Stop AI only stops the current deployment.

### 8) GUI asset version was bumped forward
The GUI app version was updated to `0_3_9` so the browser is more likely to fetch the new JS/CSS/template state after patching.

## Verification actually performed
- Reconstructed the current forward CustomDrive state from:
  - `CustomDrive_0_3_0.zip`
  - `CustomDrive_0_3_1_patch.zip`
  - `CustomDrive_0_3_2_patch.zip`
  - `CustomDrive_0_3_3_patch.zip`
  - `CustomDrive_0_3_4_patch.zip`
  - `CustomDrive_0_3_5_patch.zip`
  - `CustomDrive_0_3_6_patch.zip`
  - `CustomDrive_0_3_7_patch.zip`
  - `CustomDrive_0_3_8_patch.zip`
- Re-read the patch notes listed above before editing.
- Ran Python syntax checks on:
  - `custom_drive/arm_service.py`
  - `custom_drive/object_detection_service.py`
  - `custom_drive/gui_control_app.py`
- Ran JS syntax check on:
  - `custom_drive/gui_web/static/app.js`
- Ran:
  - `python -m compileall custom_drive`
- Ran a code-level smoke test with a fake `ServoKit` module to verify:
  - servo 0 direct motion starts, changes angle, and stops cleanly
  - servo 1 direct motion starts, changes angle, and stops cleanly
  - direct-servo status fields update as expected
- Ran a small object-detection service smoke test to verify:
  - the new AI undeploy path leaves the active model as `none`

## Known limits / next steps
- I did **not** claim live Pi hardware validation in this container.
- This patch changes the current GUI arm workflow to direct servo control, but it intentionally leaves legacy grouped backend actions in place for compatibility.
- If you later want custom labels for servo 0 and servo 1, that can be added as a small follow-up without changing the new control model.
- If you want Stop AI to also force overlay-disabled in config, that can be added later, but I intentionally left overlay settings intact so stopping deployment does not wipe user tuning.
