# PATCH NOTES — piTrainer_0_8_3 Exported TFLite Validation Page

## Request summary
- Build forward from the V8 piTrainer line.
- Add an Export Validation page after Export.
- Keep the same general format as the existing model Validation tab, but validate only the exported `.tflite` model.
- Use this to diagnose cases where the TFLite model loaded on the car gives a narrow output range that does not agree with normal model validation.

## Cause / root cause
- The existing `4 Validate` page validates the in-memory trained Keras model or a saved `.keras` / `.h5` model through `model.predict(...)`.
- The car runtime loads the exported `.tflite` artifact, so a mismatch can happen after export/conversion or inside TFLite tensor input/output handling.
- Without validating the actual exported `.tflite` file in piTrainer, it is difficult to tell whether the narrow output range is caused by:
  - the trained model itself;
  - the export/conversion step;
  - TFLite input scaling, tensor shape, quantization/dequantization, or output ordering;
  - car-side runtime loading/inference code.

## Files changed
- `piTrainer/piTrainer/main_window.py`
  - Adds `6 Export Validation` after `5 Export`.
  - Adds `Ctrl+6` to open Export Validation.
  - Adds `Ctrl+Shift+E` to run Export Validation.
  - Refreshes and saves the new page layout with the rest of the app.
- `piTrainer/piTrainer/pages/export_validation_page.py`
  - New page using the same three-column pattern as Validation:
    - Export Validation Workflow;
    - Export Validation Plot / Log;
    - Export Validation Frame Review.
  - Uses only an exported `.tflite` file for prediction.
- `piTrainer/piTrainer/panels/export_validation/__init__.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_actions_panel.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_config_panel.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_summary_panel.py`
  - New config/actions/summary panels for TFLite validation.
  - Allows browsing for `.tflite` files or using the last/newest file from the Export folder.
- `piTrainer/piTrainer/services/validation/validation_service.py`
  - Adds a real TFLite validation path using `tensorflow.lite.Interpreter`, falling back to `tflite_runtime.Interpreter` when available.
  - Keeps the existing Keras/current-model validation path.
  - Shares result building, plotting, frame review, and summary output between normal Validation and Export Validation.
  - Reports TFLite prediction output ranges for steering and speed.
  - Handles float and quantized TFLite input/output tensors where quantization metadata is available.
- `piTrainer/piTrainer/pages/export_page.py`
  - Links the newly created `.tflite` artifact to Export Validation after a successful export.
  - Updates the page step number to `5 of 6`.
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
  - Updates page step labels from `of 5` to `of 6`.
- `piTrainer/piTrainer/app_state.py`
  - Adds `last_exported_tflite_path` so Export can pass the latest `.tflite` path to Export Validation.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.8.3` / `piTrainer_0_8_3`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the new Export Validation page and the six-step workflow.
- `piTrainer/AGENTS.md`
  - Adds anti-rollback guidance for the new Export Validation page.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_3.md`
  - This patch note.

## Exact behaviour changed
- A new final top-level tab is available:
  - `6 Export Validation`
- The normal validation page remains:
  - `4 Validate`
- `4 Validate` still validates the current trained model or external `.keras` / `.h5` model.
- `6 Export Validation` validates only an exported `.tflite` model through a TFLite interpreter.
- Export Validation reuses the familiar validation review format:
  - run/config controls on the left;
  - prediction plots and logs in the middle;
  - frame-level best/worst/bad prediction review on the right.
- After Export creates a `.tflite` file, the latest `.tflite` path is automatically linked into Export Validation.
- The user can still browse manually to any `.tflite` file, including the exact file copied to the car.
- Export Validation summary/log now shows prediction ranges, for example steering min/max/mean and speed min/max/mean, so narrow output can be seen quickly.

## Behaviour intentionally not changed
- The existing `4 Validate` Keras/current-model validation page remains available.
- Training, preprocessing, data loading, generated-row hiding, and edit redirection remain unchanged except for page count labels.
- Export artifact creation remains unchanged except for linking the exported `.tflite` path to Export Validation.
- The accepted `0.8.1` Export-first tab order remains unchanged:
  - `1 Export`
  - `2 Status`
- The accepted `0.8.2` Data page pandas warning fix remains unchanged.
- No runtime/user config files are reset.

## Compatibility notes
- This is a patch-only zip for the V8 piTrainer line, intended to apply after `piTrainer_0_8_2_patch.zip`.
- Export Validation needs either TensorFlow or `tflite-runtime` installed in the active environment to run the `.tflite` interpreter.
- `requirements.txt` already includes TensorFlow for the trainer workflow, so a normal full piTrainer environment should have `tensorflow.lite.Interpreter` available.
- Because the visible app version is now `0.8.3`, any enabled online version-gate manifest must allow `0.8.3` before this patched app can open under release-control mode.

## Rollback-risk check
- Built forward from:
  - `piTrainer_0_8_0.zip`
  - plus accepted `piTrainer_0_8_1_patch.zip`
  - plus accepted `piTrainer_0_8_2_patch.zip`
- Checked the latest and previous three relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_8_2.md`
  - `PATCH_NOTES_piTrainer_0_8_1.md`
  - `PATCH_NOTES_piTrainer_0_8_0.md`
  - `PATCH_NOTES_piTrainer_0_7_3.md`
- Confirmed this patch does not intentionally roll back:
  - the `0.8.1` Export-first tab layout;
  - the `0.8.2` Data page pandas warning fix;
  - V8 generated-data workflow baseline;
  - V7.3 version-gate implementation;
  - V7.2 generated-data hiding and edit redirection;
  - V7.1 horizontal-flip label safety.

## Verification actually performed
- Inspected the real V8 file tree, then applied the accepted `0.8.1` and `0.8.2` patches before editing.
- Checked the real entry point remains:
  - `piTrainer/main.py`
- Confirmed `6 Export Validation` is added after `5 Export` in `main_window.py`.
- Confirmed the normal `4 Validate` page remains present.
- Confirmed the Export page still keeps `1 Export` before `2 Status`.
- Confirmed all page banner step labels now use six workflow steps.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a lightweight helper check for the shared validation result/summary code and TFLite single-output splitting logic.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox because PySide6 is not installed here.
- Real TensorFlow Lite inference on an exported `.tflite` model was not run in this sandbox because no trained/exported model artifact and image dataset were provided for this validation pass.
- Real car/Pi runtime inference was not tested.
- The online version-gate manifest was not checked or edited.

## Known limits / next steps
- Export Validation proves what the exported `.tflite` does inside piTrainer. If Export Validation looks correct but the car still gives narrow outputs, the next likely area to inspect is the Pi-side TFLite input preprocessing/output parsing path.
- If TFLite output tensor names do not clearly identify steering and speed, the validator falls back to output order `[steering, speed]` and logs that note. If a future exported model reverses output order, add a manual output mapping option.
- This patch does not change the car runtime inference code.
