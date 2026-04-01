# PATCH NOTES — CustomDrive 0_4_6

## Request summary
Add a **new Mission 1 web GUI** as a separate script/app so Mission 1 session work can be done without overwriting the older CustomDrive GUI/manual flows.

Requested behavior:
- set the Mission 1 **start route** in the web GUI using the same typed flag style as before, for example:
  - `--forward 2 --turn-right 5 --forward 5 --turn-right 5`
- upload and set the **AI model** in the web GUI
- run the **start route first**
- **after the start route**, turn on the camera, deploy the AI model, get AI output
- if **class 1** is detected, the car should **drive toward class 1**

## Root cause / why a new script was added
The repo snapshot available in this chat still shows an older CustomDrive line, while the accepted project history described in chat is newer.

To reduce rollback risk, this patch was implemented as a **new additive Mission 1 web app** instead of replacing the existing `run_custom_drive_web.py` or `manual_control_app.py` flows.

That keeps the new Mission 1 session work isolated while still reusing existing repo services:
- PiServer `CameraService`
- PiServer `MotorService`
- CustomDrive-style project paths and JSON config patterns
- CustomTrainer Pi-side TFLite detection logic as a reference for the detector parser

## Files added
- `CustomDrive/run_mission1_stage_test_demo.py`
- `CustomDrive/config/mission1_session.json`
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_tflite_detector.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_6.md`

## Exact behavior changed
### 1. New Mission 1 web launcher
Added a new launcher:
- `python run_mission1_stage_test_demo.py`

This starts a dedicated Mission 1 session web app.

### 2. Web GUI can store and edit the start route
The new GUI stores its settings in:
- `CustomDrive/config/mission1_session.json`

The start route is entered as free-form typed flags and is parsed **in the exact order typed**.

Supported route flags in this patch:
- `--forward SECONDS`
- `--backward SECONDS`
- `--turn-right SECONDS`
- `--turn-left SECONDS`

The parser is sequential, so a route such as:
- `--forward 5 --turn-right 5 --forward 3 --turn-left 5`

will execute in that same order.

### 3. AI model upload + load from the Mission 1 page
The new Mission 1 page can:
- upload a `.tflite` model
- list uploaded models
- load/select the active model for the session

Uploaded models are stored under:
- `CustomDrive/models/mission1/`

### 4. Mission flow now matches the requested order
When the Mission 1 session starts:
1. parse the typed start route
2. run the start route using PiServer `MotorService`
3. after the route completes, start PiServer `CameraService`
4. run the loaded TFLite model on the live camera frames
5. if target **class 1** is detected, steer/drive toward it

### 5. Safe tracking behavior for class 1
The tracking loop currently behaves as follows:
- if class `1` is **not** detected, the car stops and waits
- if class `1` **is** detected:
  - steering is driven from horizontal error to the target box
  - throttle is only applied when the target is close enough to centered
- if the target reaches the configured bottom-ratio threshold, the car stops and marks the session as complete

This was chosen as a safer default than blind search movement.

## Verification actually performed
Performed in this container:
- reviewed the real `CustomDrive/` repo structure before patching
- reviewed the latest available CustomDrive patch notes in the repo snapshot (`0_1_6` to `0_1_9`) to avoid overwriting newer manual-control/arm work in that snapshot
- confirmed the new Mission 1 app is **additive** and does not replace:
  - `run_custom_drive_web.py`
  - `custom_drive/web_app.py`
  - `run_custom_drive_manual.py`
  - `custom_drive/manual_control_app.py`
- checked that the new code reuses the real repo service paths for:
  - PiServer `CameraService`
  - PiServer `MotorService`
- ran Python compile verification on the new files

## Compile verification
Checked with:
```bash
python -m compileall CustomDrive
```
for the new patch files in the patch workspace.

## Known limits / next steps
- This patch expects a **TFLite object-detection model** whose output format is compatible with the included parser logic.
- The current Mission 1 flow tracks **class id `1`** numerically. For stability, the detection payload exposed to the Mission 1 UI currently uses numeric class ids instead of optional label names.
- No real Pi hardware verification was possible in this container, so live camera bring-up, motor motion, and real field tuning still need to be tested on the Pi.
- The route parser currently supports the four timed flags listed above. If you want more route commands later, they can be added without changing the existing order-preserving parser style.
- This patch intentionally avoids touching existing CustomDrive GUI/manual code to reduce rollback risk against the accepted newer CustomDrive line described in chat.
