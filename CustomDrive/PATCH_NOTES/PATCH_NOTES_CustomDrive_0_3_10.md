# CustomDrive 0_3_10 Patch Notes

## Request summary
Apply a forward patch on top of the accepted `0_3_9` CustomDrive state so that:
- the direct-servo arm panel is reordered with **servo 0 on the first row** and **servo 1 on the second row**,
- and the current direct-servo motion speed is increased **another 2x**.

## Anti-rollback review performed
Before patching, I checked:
- the current reconstructed code state built forward from `CustomDrive_0_3_0` through the accepted `0_3_9` patch,
- the latest patch note: `0_3_9`,
- the previous three recent notes: `0_3_8`, `0_3_7`, and `0_3_6`.

That review was used to avoid rolling back:
- the direct independent servo 0 / servo 1 control model,
- the square 2x2 arm button layout,
- pointer-capture press-and-hold behavior,
- startup hold / stop hold / keepalive hold refresh,
- serialized ServoKit/PCA9685 writes,
- gripper isolation on servo 2,
- the AI Stop button and current AI settings layout.

## Root cause / design issue
Two small but real follow-up adjustments were needed after `0_3_9`.

### 1) Button order did not match the requested row grouping
`0_3_9` built the new 2x2 direct-servo square, but the button order still grouped by direction:
- first row = `Servo 0 +`, `Servo 1 +`
- second row = `Servo 0 -`, `Servo 1 -`

The new request was to group by servo instead:
- first row = **servo 0** controls
- second row = **servo 1** controls

### 2) Current motion speed still used the earlier 2x speed baseline
Earlier arm patches already doubled speed once. The new request was to double the current direct-servo speed again.

The current runtime still fell back to the earlier `speed_multiplier = 2.0` baseline when a saved config did not explicitly define `speed_multiplier`, so a forward update was needed in the current default/fallback path.

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_3_10.md`

## Exact behavior changed

### 1) Direct-servo rows are now grouped by servo
The 2x2 arm square still exists, but the button order is now:
- row 1: `Servo 0 +`, `Servo 0 -`
- row 2: `Servo 1 +`, `Servo 1 -`

This keeps the current square layout while matching the requested row grouping.

### 2) Default arm speed baseline increased from 2.0 to 4.0
The forward runtime default/fallback for `speed_multiplier` is now `4.0` instead of `2.0`.

That means installs that are still using the default/fallback arm speed path will now move about **2x faster than the current 0_3_9 baseline**.

This change affects:
- direct servo 0 / servo 1 motion speed
- gripper motion speed on servo 2

### 3) GUI asset version bumped forward
The GUI app version was updated to `0_3_10` so the browser is more likely to fetch the new page order after patching.

## Verification actually performed
- Re-read the latest patch note and recent related notes listed above before editing.
- Inspected the real current arm UI and backend files in the active forward CustomDrive state.
- Ran Python syntax checks on:
  - `custom_drive/manual_control_config.py`
  - `custom_drive/arm_service.py`
  - `custom_drive/gui_control_app.py`
- Ran:
  - `python -m compileall custom_drive`
- Verified the HTML arm button order is now grouped by servo rows.
- Verified the runtime fallback/default speed multiplier is now `4.0`.

## Known limits / next steps
- I did **not** claim live Pi hardware motion timing validation in this container.
- This patch updates the runtime default/fallback speed path. If a specific Pi already has an explicit saved `speed_multiplier` in `config/manual_control.json`, that explicit saved value still wins unless you update that config.
- If you later want separate speed controls for servo 0, servo 1, and gripper, that should be a follow-up schema change rather than forcing it into this small patch.
