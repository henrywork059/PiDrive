# PATCH NOTES — CustomDrive_0_5_12

## Request summary
Patch the current CustomDrive Mission 1 line to address three connected issues:

1. The user found a live turning bug: when Mission 1 was asked to **turn right**, the current motor output pattern was showing **left motor reverse + right motor forward**, which on the user's car caused the vehicle to go left instead of right.
2. Because the actual physical motor / gearbox / wiring direction cannot be assumed, the Mission 1 web GUI needed a practical **motor-direction control** in the new Motor Status panel, similar to PiServer motor direction configuration.
3. The user explicitly asked that this motor-rotation logic also apply to the **start routing** section, not only the live AI/search motion.

## Baseline / rollback review
This patch was built forward from the current accepted CustomDrive Mission 1 line represented in the workspace by:
- repo CustomDrive baseline
- accepted Mission 1 patches through `0_5_11`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_8.md`
- `PATCH_NOTES_CustomDrive_0_5_9.md`
- `PATCH_NOTES_CustomDrive_0_5_10.md`
- `PATCH_NOTES_CustomDrive_0_5_11.md`

Accepted behavior intentionally preserved:
- route -> camera -> model -> AI loop startup order
- Mission 1 pickup / drop-off state machine
- stop-before-grip / stop-before-release stage split
- live Pi-side frame overlay
- Arm Position panel
- Motor Status panel
- current Mission 1 motor-service based turn path from `0_5_5`
- start-route executor from `0_5_6`

## Cause / root cause found
The current Mission 1 line had a real usability gap around motor calibration.

### 1. Mission 1 turning already depends on `steering_direction`, but the Mission 1 web GUI could not change it
Mission 1 turn commands already use the shared calibrated `MotorService.update(...)` path. That means live turning and route turning both depend on the persisted PiServer motor config, especially:
- `left_direction`
- `right_direction`
- `steering_direction`

So the turning problem the user observed was not best fixed by hardcoding a new assumed right-turn polarity in Mission 1. The safer fix was to expose the real direction controls in Mission 1 itself so the user can calibrate the car on the actual hardware.

### 2. Start-route turning also needed to follow the same calibrated direction settings
The user explicitly asked that the motor-rotation logic be linked to the start-route section. The current Mission 1 route executor already uses `_turn_in_place(...)`, which uses `MotorService.update(...)`, but there was no Mission 1 UI path to adjust and persist those direction settings from the Mission 1 page.

### 3. No Mission 1 API existed for saving motor direction config
The web page only had status visibility for the motors. There was no Mission 1 API route for:
- reading current motor direction config
- saving updated motor direction config
- immediately applying it to the active `MotorService`
- persisting it back to the PiServer runtime config used by future sessions

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_12.md`

## Exact behavior changed

### 1. Mission 1 now exposes motor direction config controls in the Motor Status panel
The Motor Status panel now includes live controls for:
- left motor direction
- right motor direction
- steering / turn direction

Each can be set to:
- `Normal (+1)`
- `Inverted (-1)`

A quick button was also added:
- **Flip turn direction**

This is the practical fix for the user-reported right-turn bug on real hardware.

### 2. Mission 1 can now save and apply motor direction config directly from the web GUI
A new Mission 1 backend API was added:
- `GET /api/motor/config`
- `POST /api/motor/config`

The save path now:
1. normalizes the requested direction values to `+1` / `-1`
2. merges them into the persisted PiServer runtime motor config
3. applies them immediately to the active Mission 1 `MotorService`
4. records a truthful Mission 1 motor event

### 3. Start-route turning now uses the same persisted motor direction settings from Mission 1
Mission 1 now reapplies the persisted motor defaults at the start of each new session before the route begins.

That means the direction settings changed in the Mission 1 Motor panel now carry into:
- start-route turns
- pickup search rotation
- target tracking turns
- drop-off search rotation
- later Mission 1 sessions after restart

### 4. Motor status payload now includes the current direction config
The Mission 1 motor status payload now includes:
- `left_direction`
- `right_direction`
- `steering_direction`

This lets the web panel show the currently active calibration state alongside live wheel outputs.

### 5. No hardcoded guess about physical car direction was introduced
This patch intentionally does **not** hardcode a new universal “right turn means this exact wheel polarity on every car” assumption.

Reason:
- the user explicitly noted that the actual motor rotation direction cannot be predicted from code alone
- different hardware / wiring / motor direction settings can change the physical result

So this patch fixes the issue in the safer way: by exposing the real calibration controls directly in the Mission 1 GUI and making them apply to both live motion and start routing.

## Verification actually performed
The following checks were actually performed in the patched workspace:

- inspected the current Mission 1 motor path in `mission1_session_app.py`
- confirmed route turning and live turning both use the shared motor-service path
- inspected the current Motor Status panel JS and confirmed it was read-only before this patch
- added backend save/apply logic for motor directions
- added Mission 1 web controls for motor directions and quick turn-direction flip
- ran `python -m py_compile custom_drive/mission1_session_app.py`
- ran `node --check custom_drive/mission1_web/static/app.js`
- ran `python -m compileall custom_drive`

A full Flask app import smoke test was attempted, but it could not be completed in this container because `flask` is not installed in the container environment used for packaging.

## Known limits / next steps
- This patch gives the user the correct calibration controls, but it still requires one real-hardware test to choose the correct turn direction for the user's car.
- The current Mission 1 Motor panel now supports direction calibration only. It does not yet expose additional PiServer motor tuning fields such as:
  - left / right max speed
  - left / right bias
- If the user wants, the next forward patch can expose those extra motor tuning fields in the same Motor panel as well.
