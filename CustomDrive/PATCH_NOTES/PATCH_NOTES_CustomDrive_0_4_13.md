# PATCH NOTES — CustomDrive_0_4_13

## Request summary
Rebuild the Mission 1 web session pipeline so it follows this explicit sequence and data flow:

1. In the web GUI, set the typed start route in the same ordered CLI-style format as before, for example:
   - `--forward 2 --turn-right 5 --forward 5 --turn-right 5`
2. In the web GUI, upload and set the AI model.
3. When the Mission 1 run starts, the car must:
   - run the full start route first
   - then turn on the camera
   - then load the selected AI model
4. For each AI cycle after that, the Pi must:
   - take a frame
   - pass that frame to the model
   - receive the model output
   - draw boxes and class IDs onto that frame on the Pi side
   - post the annotated frame to the web UI
   - upload the detected-object data to the web UI
   - repeat with the next frame
5. The web UI must show, for each detected object in the current frame:
   - class ID
   - centre coordinates
   - box size
   - confidence
6. The coordinate system must follow the requested Mission 1 convention:
   - frame centre is `(0, 0)`
   - left is negative `x`
   - down is negative `y`
7. The real-time FPS must be calculated and shown.
8. If the target class is detected, movement must follow this rule:
   - use the target object's `x` coordinate to decide turn direction
   - `x < 0` -> turn left
   - `x > 0` -> turn right
   - turn magnitude is based on `|x * k|`
   - `k` must be user-settable in the web GUI
   - if `|x| < 5%` of the whole frame width, the car drives forward
   - turning must be done by driving the two motors in opposite directions

The user also asked that this patch be carefully checked for naming/foldering issues and documented in enough detail for future development.

## Cause / root cause
The existing Mission 1 session line up to `0_4_12` had drifted into repeated left/right steering patches around the earlier target-follow implementation.

That older implementation was still built around:
- a left / centre / right steering-zone tracker
- mixed steering/throttle style control
- browser-side overlay assumptions from the older viewer flow

That did **not** match the new requested Mission 1 pipeline, which is structurally different:
- Pi-side annotated-frame generation
- Pi-side object list upload
- centre-origin coordinate reporting
- explicit route -> camera -> model -> per-frame inference sequencing
- direct target-`x` control with in-place opposite-direction turning

So the correct fix was **not** another small sign flip. The correct fix was to rebuild the Mission 1 session loop to match the requested pipeline directly.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/templates/index.html`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/custom_drive/mission1_web/static/styles.css`
- `CustomDrive/run_mission1_stage_test_demo.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_13.md`

## Exact behavior changed

### 1. Mission 1 runtime pipeline was rebuilt
The Mission 1 session thread now runs in this order:
- `start_route`
- `camera_boot`
- `model_boot`
- `ai_loop`

That means:
- the camera is **not** turned on during the route phase
- the model is **not** loaded until after the route is done and the camera has started
- the AI loop only begins after both of those boot stages complete

### 2. Model upload / selection behavior now matches the requested flow
Mission 1 model handling now behaves like this:
- uploading a `.tflite` model saves it and marks it as the selected Mission 1 model
- choosing a model in the web UI sets the selected model for the next Mission 1 run
- the selected model is only **loaded by the Pi during the Mission 1 run after the route finishes**

This was changed deliberately so the runtime sequence follows the requested pipeline.

### 3. Pi-side annotated frame generation was added as the main viewer output
The Mission 1 AI loop now:
- gets a frame from `CameraService`
- runs TFLite detection with `Mission1TFLiteDetector`
- converts detections into structured Mission 1 object rows
- draws boxes and class IDs onto the frame on the Pi side
- draws the centre lines / deadband guide onto the frame on the Pi side
- encodes the annotated frame as JPEG
- serves that annotated JPEG through `/api/frame.jpg`

The web viewer now displays the **Pi-generated annotated frame** instead of depending on the older browser-side SVG overlay path.

### 4. Detected-object list was rebuilt for the requested coordinate convention
For every detected object in the current AI output, the Mission 1 status payload now includes:
- `class_id`
- `confidence`
- `center.x`
- `center.y`
- `box.width`
- `box.height`
- the raw box corners
- whether the object belongs to the current target class

The Mission 1 coordinate conversion now follows the requested rule:
- frame centre = `(0, 0)`
- `x = object_center_x - frame_center_x`
- `y = frame_center_y - object_center_y`

So:
- left of centre -> negative `x`
- right of centre -> positive `x`
- above centre -> positive `y`
- below centre -> negative `y`

### 5. Mission 1 web UI now shows the current object table
The Mission 1 page now includes a dedicated detected-object table showing, for the current frame:
- class ID
- confidence
- centre X
- centre Y
- box width
- box height
- whether the row is the target class

The target-class rows are highlighted.

### 6. Real-time Mission 1 pipeline FPS was added
The Mission 1 backend now measures:
- processed AI-loop FPS
- processed AI-loop cycle time in milliseconds

These values are included in the status payload and shown in the Mission 1 status area.

This is separate from the camera backend FPS exposed by `CameraService`.

### 7. Target-follow control was replaced with target-`x` logic
The earlier zone-driven follow logic was replaced with the requested direct `x`-coordinate rule.

For the selected target class:
- if no target object is found, the car stops
- if `|x| < target_x_deadband_ratio * frame_width`, the car drives forward
- otherwise the car turns based on:
  - `turn_speed = min(turn_speed_max, |x| * turn_k)`

The web GUI now exposes the Mission 1 tuning values used by this new control rule:
- `forward_speed`
- `turn_k`
- `turn_speed_max`
- `target_x_deadband_ratio`

Default deadband is `0.05` to match the requested “5% of whole frame” rule.

### 8. Turning is now performed with opposite motor directions
The Mission 1 AI turning path no longer relies on the earlier steer-mix turning behavior.

Instead, when the target is outside the forward deadband:
- left turn -> left motor reverse, right motor forward
- right turn -> left motor forward, right motor reverse

This is done with a direct-motor command helper that still respects the saved PiServer motor tuning and per-side direction settings.

### 9. Route parsing compatibility was kept
The Mission 1 route parser still supports the ordered CLI-style route format and respects the typed order of flags, including:
- `--forward SECONDS`
- `--turn-right SECONDS`
- `--turn-left SECONDS`
- `--backward SECONDS`

The ordered token parsing was preserved rather than replaced.

### 10. Config safety was kept
This patch deliberately **does not ship a replacement `config/mission1_session.json` file**.

Reason:
- the Mission 1 config is treated as persistent user/runtime data
- shipping a config file in the patch would risk overwriting the user's existing Mission 1 settings

Instead:
- the loader now normalizes and adds the new Mission 1 keys safely
- the older Mission 1 tuning keys are still preserved in saved config for backward compatibility where practical

## Verification actually performed
The following checks were actually performed during patch work:

1. Inspected the real CustomDrive repo structure and the existing Mission 1 files rather than guessing paths.
2. Reviewed the latest accepted Mission 1 patch notes available locally:
   - `0_4_9`
   - `0_4_10`
   - `0_4_11`
   - `0_4_12`
3. Confirmed the new work was isolated to the Mission 1 session path and did not touch:
   - CustomDrive manual app
   - older CustomDrive generic web app
   - shared PiServer service files
4. Ran:
   - `python -m compileall CustomDrive`
   and compile completed successfully in the merged test workspace.
5. Ran a lightweight code-level Mission 1 sanity check (with a stubbed Flask import in the test environment) to verify:
   - ordered route parsing still works
   - centre-origin coordinate conversion gives negative `x` for left-side objects and positive `x` for right-side objects
   - target selection returns the requested class
   - the Mission 1 status payload includes the new pipeline/object-coordinate fields
6. Checked patch packaging structure so the patch zip contains only changed/new files plus patch notes under the top-level `CustomDrive/` folder.

## Known limits / next steps
1. This patch was verified at code level, but **not** with real Pi hardware in this environment.
   That means the following still require on-car validation:
   - actual camera feed timing on the Pi
   - actual TFLite model output shape for the user's model
   - actual physical left/right motor motion on the car

2. The direct-motor turning helper respects saved PiServer motor tuning and side-direction settings, but the final physical turn direction still depends on the real hardware setup and persisted motor config on the Pi.

3. `Mission1TFLiteDetector` still assumes the user's TFLite model is detection-compatible with the supported output parsing path already present in CustomDrive. If the user's model uses a materially different output format, a follow-up detector parser patch may be needed.

4. The Mission 1 web page now shows the current frame's detection table and annotated frame, but it still refreshes by polling. If needed later, this can be upgraded to a streaming/event-driven UI.

5. The Mission 1 AI loop currently chooses the control target as the highest-ranked detection of the requested target class. If later mission behavior requires multi-target priority rules, that should be added as a separate Mission 1 policy patch rather than mixed into this pipeline patch.
