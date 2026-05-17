# PiSD 0.5.2 Patch Notes — Scripted Autopilot replaced by AI Mode

## Request summary

The user asked to remove the scripted Autopilot concept and replace it with an AI model based mode.

The requested AI workflow is:

- Manual mode records training data.
- AI Mode loads a trained model.
- A safety layer must sit between AI predictions and motor output.

## Baseline / anti-rollback check

Baseline used: uploaded `PiSD_0_5_0.zip` stable/reference package.

This patch was also checked against the previously generated `PiSD_0_5_1_patch.zip` notes because `0_5_1` introduced the scripted Autopilot page. The `0_5_1` scripted profiles are intentionally superseded by this patch.

Accepted v5/v4 behaviour preserved:

- Manual Drive overlay toggle and predicted path overlay remain intact.
- Manual Drive overlay calibration/debug panel remains intact.
- Manual Drive STOP/status refresh/page-leave fail-safe behaviour remains intact.
- Manual Drive preview idle/FPS/stale-state behaviour remains intact.
- Recording/snapshot folder selection/download/delete behaviour remains intact.

## Cause / root cause

The previous Autopilot foundation used bounded scripted profiles. That was safe for bench testing, but it did not match the intended DonkeyCar/JetRacer-like workflow where the car learns from manually recorded frames and steering/throttle labels.

PiSD therefore needed a real AI-mode foundation rather than a scripted mode labelled as autopilot.

## Files changed

- `PiSD/pisd/__init__.py`
  - Bumped version to `0.5.2`.
- `PiSD/pisd/app.py`
  - Added `/ai-mode` page.
  - Added `/autopilot` compatibility alias that opens AI Mode instead of scripted Autopilot.
  - Added AI status to `/api/status`.
  - Added AI error history to `/api/errors`.
  - Added AI APIs.
  - Manual Drive and global STOP now stop AI Mode first.
- `PiSD/pisd/core/errors.py`
  - Added `PISD-AI-*` error codes.
  - Added `PISD-TEST-025` for AI Mode validation.
- `PiSD/pisd/core/settings_manager.py`
  - Added persisted and clamped `ai_mode` settings.
- `PiSD/pisd/services/ai_drive_service.py`
  - Added AI model listing/loading, optional TFLite/Keras runtime hooks, prediction path, guarded AI loop, and safety limiter.
- `PiSD/pisd/services/autopilot_service.py`
  - Replaced the scripted Autopilot service with a deprecated no-script compatibility shim.
- `PiSD/pisd/services/recording_service.py`
  - Added `labels.jsonl` training-label output beside full `records.jsonl` metadata.
  - Added training-label metadata to manifests.
- `PiSD/pisd/web/templates/front_page.html`
  - Added AI Mode card.
  - Updated Manual Drive card wording to mention AI training labels.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Clarified that recordings include both `records.jsonl` and `labels.jsonl`.
- `PiSD/pisd/web/templates/ai_mode.html`
  - Added the AI Mode UI.
- `PiSD/pisd/web/static/css/ai_mode.css`
  - Added AI Mode page styling.
- `PiSD/pisd/web/static/js/ai_mode.js`
  - Added AI Mode model list/load/config/start/stop/status browser logic.
- `PiSD/pisd/web/templates/autopilot.html`
  - Retired stale scripted Autopilot template and redirects users to AI Mode.
- `PiSD/pisd/web/static/css/autopilot.css`
  - Retired stale scripted Autopilot CSS.
- `PiSD/pisd/web/static/js/autopilot.js`
  - Retired stale scripted Autopilot JS and redirects stale references to AI Mode.
- `PiSD/scripts/test_ai_mode_page.py`
  - Added AI Mode page/static/API contract checks.
- `PiSD/scripts/test_ai_drive_service.py`
  - Added AI service safety/model-listing checks.
- `PiSD/scripts/test_recording_service.py`
  - Added checks for `labels.jsonl` training labels.
- `PiSD/scripts/test_front_page_tabs.py`
  - Added AI Mode card/static route checks.
- `PiSD/scripts/run_standard_validation.py`
  - Added AI Mode static/source validation to the standard checklist.
- `PiSD/docs/ERROR_CODES.md`
  - Documented AI Mode error codes.
- `PiSD/README.md`
  - Documented AI Mode workflow and validation commands.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_5_2.md`
  - Added these patch notes.

## Exact behavior changed

### 1. Scripted Autopilot is no longer active

The old scripted profiles are not used by the app anymore.

The old `/autopilot` path is kept only as a compatibility alias to the new AI Mode page. If a Pi already had the `0_5_1` scripted Autopilot files, this patch overwrites the active service with a deprecated no-script shim and replaces stale Autopilot static/template files with redirect/retired files.

### 2. New AI Mode page

New page:

```text
/ai-mode
```

The front page now includes an AI Mode card.

AI Mode includes:

- model list from `PiSD/models/`;
- load model button;
- one-shot prediction button;
- preview-only AI start;
- guarded AI drive start;
- STOP AI + motors;
- camera preview controls;
- raw prediction display;
- safety-limited command display;
- left/right motor output display;
- inference time and loop rate display.

### 3. AI model folder support

Supported model discovery extensions:

```text
.tflite, .keras, .h5, .onnx, .pt
```

Runtime inference hooks are implemented for:

- `.tflite` when `tflite_runtime` or TensorFlow Lite support is installed;
- `.keras` / `.h5` when TensorFlow is installed.

`.onnx` and `.pt` files are listed for visibility but are refused as runnable until a future backend is added.

### 4. Manual Drive recording now writes training labels

Every captured/recorded frame now writes:

- full trace/debug metadata in `records.jsonl`;
- compact trainer-friendly labels in `labels.jsonl`.

Example `labels.jsonl` fields:

```json
{"frame":"frames/frame_000001_xxx.jpg","relative_file":"recordings/.../frames/frame_000001_xxx.jpg","steering":0.12,"throttle":0.18,"timestamp_utc":"...","source_frame_seq":1,"session_id":"..."}
```

This gives a direct dataset format for future trainer work:

```text
camera frame -> steering label + throttle label
```

### 5. Safety layer between AI and motors

AI raw model output is never sent directly to motors.

The `AIDriveService.apply_safety(...)` layer clamps and smooths AI output using persisted settings:

- `max_throttle`;
- `max_steering`;
- `fixed_throttle` for steering-only mode;
- `steering_smoothing`;
- `throttle_smoothing`;
- `update_hz`;
- motor-output arm state.

Guarded AI drive is refused unless:

- a runnable model is loaded;
- safety acknowledgement is checked;
- motor output is enabled when real hardware output is active.

### 6. Manual and global STOP stop AI first

`/api/control/manual` stops AI Mode before applying a manual command.

`/api/control/stop` stops AI Mode and then stops motors.

This prevents AI Mode and Manual Drive from fighting over the motor service.

## Verification actually performed

Performed locally after applying the patch over the uploaded `PiSD_0_5_0` baseline:

- `python3 -m compileall -q pisd scripts` — passed.
- `node --check pisd/web/static/js/ai_mode.js` — passed.
- `node --check pisd/web/static/js/autopilot.js` — passed.
- `node --check pisd/web/static/js/manual_drive.js` — passed.
- `python3 scripts/test_ai_drive_service.py` — passed.
- `python3 scripts/test_recording_service.py` — passed.
- `python3 scripts/test_ai_mode_page.py --static-only` — passed.
- `python3 scripts/test_front_page_tabs.py --static-only` — passed.
- `python3 scripts/test_manual_drive_page.py --static-only` — passed.
- `python3 scripts/test_settings_persistence.py` — passed.
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor` — passed.

## Known limits / not verified

- Full Flask route tests were not completed in this container because Flask is not installed here.
- Real Raspberry Pi camera/motor hardware behavior was not tested in this container.
- AI runtime loading was not tested with a real trained `.tflite` or `.keras` model in this container.
- `.onnx` and `.pt` model files are listed but not runnable yet.
- This patch adds the AI runtime foundation and safety layer. A future trainer/export patch is still needed to create models from `labels.jsonl` automatically.

## Apply

From the PiDrive parent folder:

```bash
cd ~/PiDrive
unzip -o PiSD_0_5_2_patch.zip
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard refresh the browser with `Ctrl + F5` so the `v=0.5.2` static assets are loaded.
