# PATCH NOTES — piTrainer_0_8_5 Ordered TFLite Output Export Fix

## Request summary
- Build forward from the accepted V8 piTrainer patch line.
- Investigate the Export Validation plot where the exported `.tflite` model shows a narrow / almost constant steering output that does not agree with normal Keras validation.
- Fix the export-side issue so newly exported TFLite models expose steering and speed in a stable order for the car runtime.

## Cause / root cause
- The screenshot of `4 Validate` versus `6 Export Validation` shows a strong signature of swapped TFLite outputs:
  - normal Keras validation steering follows the diagonal reasonably;
  - Export Validation steering becomes almost a horizontal band around the normal speed value;
  - Export Validation speed becomes a vertical column where the ground-truth speed is nearly fixed but the prediction varies like steering.
- That pattern means the TFLite output tensor that piTrainer/car-side code was treating as steering is likely the speed/throttle output, and the tensor treated as speed is likely steering.
- The previous export converted the original Keras dict-output model directly to TFLite. TFLite may expose the two output tensors with generic names and an order that is not safe to assume.
- The previous Export Validation fallback used output order `[steering, speed]` when TFLite tensor names were unclear, which can produce the exact narrow steering plot shown by the user.

## Files changed
- `piTrainer/piTrainer/services/export/export_service.py`
  - Adds an ordered TFLite export wrapper.
  - New TFLite exports now expose one single 2-value output tensor ordered as `[steering, throttle/speed]`.
  - Keeps the trained network weights and image input unchanged; only the exported TFLite output interface is made stable.
  - Adds export notes that clearly state the ordered TFLite output convention.
- `piTrainer/piTrainer/services/validation/validation_service.py`
  - Improves TFLite output parsing.
  - Single-output TFLite files are read as `value[0]=steering`, `value[1]=speed`.
  - Older multi-output TFLite files with unclear tensor names can be auto-mapped against validation labels to detect swapped output tensors.
  - Adds backend notes warning when an older multi-output file appears to have output order different from the car-side assumption.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.8.5` / `piTrainer_0_8_5`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_5.md`
  - This patch note.

## Exact behaviour changed
- Newly exported `.tflite` files are no longer exported as ambiguous two-output TFLite models.
- Newly exported `.tflite` files now have a stable single output tensor:
  - index `0` = steering;
  - index `1` = throttle/speed.
- Export Validation can still inspect older TFLite files.
- If an older TFLite file has unnamed or unclear output tensors, Export Validation compares the possible output assignments against the loaded validation labels and chooses the lower-error mapping for diagnosis.
- When Export Validation detects that the likely correct mapping is swapped, its summary/backend notes tell the user to re-export the model with this patch.

## Behaviour intentionally not changed
- The normal `.keras` export path is unchanged.
- The training model architecture and loss outputs remain named `steering` and `throttle`.
- Image preprocessing remains unchanged:
  - RGB image load;
  - resize to configured train image width/height;
  - float32 scaling to `0.0–1.0`;
  - horizontal flip handling for generated rows.
- The `0.8.1` Export page remains action-first:
  - `1 Export`;
  - `2 Status`.
- The `0.8.2` pandas warning fix remains in place.
- The `0.8.3` Export Validation page remains as tab `6 Export Validation`.
- The `0.8.4` Data-page loaded-row validation and last-used model path persistence remain in place.
- No user data, datasets, runtime configs, or saved models are overwritten.

## Compatibility notes
- This is a patch-only zip for the V8 piTrainer line, intended to apply after `piTrainer_0_8_4_patch.zip`.
- Existing old `.tflite` files are not modified in place.
- Re-export the model after applying this patch, then use the new `.tflite` on the car.
- A new patched TFLite file should be easier for the car runtime to parse because it has one ordered output vector instead of ambiguous multiple output tensors.
- Because the visible app version is now `0.8.5`, any enabled online version-gate manifest must allow `0.8.5` before this patched app can open under release-control mode.

## Rollback-risk check
- Built forward from:
  - `piTrainer_0_8_0.zip`;
  - plus accepted `piTrainer_0_8_1_patch.zip`;
  - plus accepted `piTrainer_0_8_2_patch.zip`;
  - plus accepted `piTrainer_0_8_3_patch.zip`;
  - plus accepted `piTrainer_0_8_4_patch.zip`.
- Checked the latest and previous three relevant piTrainer patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_4.md`;
  - `PATCH_NOTES_piTrainer_0_8_3.md`;
  - `PATCH_NOTES_piTrainer_0_8_2.md`;
  - `PATCH_NOTES_piTrainer_0_8_1.md`.
- Confirmed this patch does not intentionally roll back:
  - Export-first tab layout from `0.8.1`;
  - Data page pandas warning fix from `0.8.2`;
  - Export Validation page and six-step workflow from `0.8.3`;
  - Data-page loaded-row validation and saved validation paths from `0.8.4`;
  - generated-row hiding and edit redirection behavior;
  - horizontal-flip label safety;
  - version-gate code path.

## Verification actually performed
- Inspected the current V8 patch state after applying patches `0.8.1` through `0.8.4` on top of `piTrainer_0_8_0.zip`.
- Reviewed the screenshot pattern and matched it to a swapped-output failure mode.
- Inspected the real export code path in `piTrainer/services/export/export_service.py`.
- Inspected the real TFLite validation code path in `piTrainer/services/validation/validation_service.py`.
- Added a helper check using fake reversed multi-output TFLite tensors:
  - input output order `[speed, steering]`;
  - validation labels with steering spread and speed near constant;
  - confirmed the auto-mapper selected `steering=output[1]`, `speed=output[0]`.
- Added a helper check using fake single-output ordered tensor `[steering, speed]` and confirmed it is parsed directly.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI clicking was not run in this sandbox.
- Real TensorFlow/TFLite conversion was not run because the user's trained `.keras` model and dataset files were not available in this sandbox.
- Real car/Pi inference was not tested.
- The online version-gate manifest was not checked or edited.

## Known limits / next steps
- Apply this patch, re-export the TFLite model, then rerun `6 Export Validation` on the newly exported `.tflite` file.
- The new Export Validation plot should no longer show steering as a narrow speed-like horizontal band if output order was the cause.
- If the newly exported TFLite validates correctly in piTrainer but the car still shows narrow steering, the next target is the car-side TFLite output parser and it should read the single vector as `[0]=steering`, `[1]=speed`.
- Old TFLite files should be treated as suspect if Export Validation reports an auto-mapped swapped output order.
