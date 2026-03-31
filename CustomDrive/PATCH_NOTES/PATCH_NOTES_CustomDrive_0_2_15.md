# CustomDrive 0_2_15 Patch Notes

## Request summary
Patch the current CustomDrive code so it is compatible with the current CustomTrainer TFLite export pipeline, without changing CustomTrainer labels.

Main requested outcomes:
- Add a TFLite perception backend to CustomDrive.
- Keep the existing color backend available as a fallback.
- Let the GUI AI overlay load a CustomTrainer-exported `.tflite` model and show the model's real labels.
- Make mission target labels configurable inside CustomDrive instead of renaming Trainer labels.
- Keep GUI, headless, and live mission code forward-compatible with the latest accepted CustomDrive state.

## Root cause
CustomDrive already had a GUI-side object-detection overlay path, but the broader CustomDrive mission/runtime pipeline was still built around the older HSV/color perception path.

The main gaps were:
1. The live mission runtime did not have a proper backend switch between color and TFLite perception.
2. Mission target labels were still effectively tied to the older default label assumptions (`he3`, `he3_zone`) instead of being clearly configurable from settings.
3. The GUI AI settings did not expose the full model-pipeline information needed for the current CustomTrainer export flow:
   - backend choice
   - labels file choice
   - input size
   - mission target label
   - drop-zone label
4. Runtime settings and GUI settings were not kept in sync, so a model selected in the GUI was not cleanly reflected into the live mission runtime configuration.

## Files changed
- `CustomDrive/custom_drive/tflite_perception.py` *(new)*
- `CustomDrive/custom_drive/perception.py`
- `CustomDrive/custom_drive/live_runtime.py`
- `CustomDrive/custom_drive/runtime_settings.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/config/runtime_settings.json`
- `CustomDrive/config/manual_control.json`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_2_15.md`

## Exact behavior changed
### 1) Added a real TFLite perception backend for CustomDrive mission/runtime
- Added `custom_drive/tflite_perception.py`.
- The new backend uses the same core TFLite object-detection preprocessing and output parsing direction as the current CustomTrainer Pi runtime:
  - letterbox resize
  - BGR -> RGB conversion
  - float / quantized tensor handling
  - YOLO-style output parsing
  - NMS
  - scaling boxes back to the source frame
- The backend returns detections in CustomDrive's existing `Detection` / `FramePerception` structures so the mission logic and overlay do not need a separate detection format.

### 2) Added a perception backend switch for live mission runtime
- Live runtime now supports:
  - `color`
  - `tflite`
- The runtime keeps backward compatibility:
  - if `perception_backend` is `color`, the older HSV pipeline still works
  - if `perception_backend` is `tflite` but no valid model path is configured, runtime stays safe and reports the reason
- Mission runtime now reads configurable labels from settings instead of assuming Trainer labels should be renamed.

### 3) Added / loaded runtime perception settings for TFLite
The runtime settings path now supports:
- `perception_backend`
- `model_path`
- `labels_path`
- `input_size`
- `confidence_threshold`
- `iou_threshold`
- `target_label`
- `drop_zone_label`

These are now normalized and persisted in `CustomDrive/config/runtime_settings.json`.

### 4) Kept Trainer labels unchanged
- The overlay now uses the labels exactly as loaded from the selected labels file / model bundle.
- No Trainer label renaming was added.
- `target_label` and `drop_zone_label` are separate CustomDrive settings, so mission logic can choose which exported class names matter.

### 5) GUI AI settings expanded to match the model pipeline
The GUI AI settings window now includes:
- perception backend select (`color` / `tflite`)
- model select
- labels file select
- input size
- confidence threshold
- IoU threshold
- overlay enable / disable
- overlay FPS
- mission target label
- mission drop-zone label

The GUI also now shows a note that runtime mission perception settings are synced into:
- `CustomDrive/config/runtime_settings.json`

### 6) GUI settings now sync into runtime settings
- Saving AI settings in the GUI now updates both:
  - `CustomDrive/config/manual_control.json`
  - `CustomDrive/config/runtime_settings.json`
- That means the live mission runtime, headless path, and GUI are using the same configured perception backend direction instead of drifting apart.

### 7) GUI overlay service now uses the new perception metadata more cleanly
- AI model listing now includes both model files and available `.txt` label files.
- Deploying a model keeps the selected labels file and mission labels in sync.
- Overlay status now exposes:
  - backend
  - active model
  - labels file
  - resolved labels path
  - resolved input size
  - target label
  - drop-zone label

## Verification actually performed
- Inspected the real uploaded CustomDrive stable baseline from `CustomDrive_0_2_0.zip`.
- Read the recent CustomDrive patch notes for `0_2_12`, `0_2_13`, and `0_2_14` before editing to avoid rolling back the recent overlay / stability direction.
- Inspected the current CustomTrainer Pi runtime export / inference path, especially:
  - `custom_trainer/assets/pi_runtime/run_tflite_detect.py`
  - `custom_trainer/services/pi_deploy_service.py`
- Reconstructed the latest accepted CustomDrive state forward from `0_2_0` plus accepted `0_2_1` to `0_2_14` patches before editing.
- Ran:
  - `python -m compileall CustomDrive`
- Ran a code-level smoke test in the container for:
  - `ObjectDetectionService.list_models()` with a sample `.tflite` + `labels.txt` + `model_config.json`
  - runtime/perception settings normalization for the new `tflite` backend

## Known limits / next steps
- I did **not** claim live Pi camera / motor / TFLite hardware runtime testing, because that was not available in this container.
- The new TFLite mission/runtime backend uses the current CustomTrainer pipeline direction, but final confirmation of visible boxes on the Pi still depends on the real Pi runtime stack (`tflite_runtime`, camera frames, uploaded model bundle).
- The current GUI overlay and the live mission runtime now share the same perception direction, but if long-runtime native segfaults continue on the Pi, the next patch should move overlay inference fully off the request path into a worker/cache loop.
