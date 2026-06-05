# PATCH NOTES — piTrainer_0_9_6 Data Model Deploy Patch

## Request summary

Add a Data page feature that lets the user deploy a trained/exported model to frame rows, view the model outputs and comparison overlay on frames, sort the Records table by largest steering or speed difference, and apply deployed model outputs to selected frame labels.

## Cause / root cause

Before this patch, piTrainer could validate models in the Validate / TFLite Check pages, but the Data page did not have a direct workflow for using model output during frame review. The user had to leave Data review to inspect prediction errors, and there was no direct way to sort loaded frame rows by model/label disagreement or overwrite selected labels from model output.

## Files changed

- `piTrainer/piTrainer/pages/data_page.py`
  - Adds a new Data Workflow tab: `4 Deploy`.
  - Wires model deploy, diff sorting, and apply-to-selected actions into the Data page.
  - Stores deployed prediction columns in the loaded DataFrames and refreshes the Records table.
  - Keeps prediction diffs updated when a deployed row is manually edited.
- `piTrainer/piTrainer/panels/data/model_deploy_panel.py`
  - New compact UI panel for model source, model path, batch size, max rows, deploy action, diff sorting, and confirmed apply-to-selected.
- `piTrainer/piTrainer/services/data/model_deploy_service.py`
  - New service that reuses existing validation/TFLite prediction paths to deploy a model over Data rows.
  - Supports current trained model, saved `.keras` / `.h5`, and `.tflite` paths.
- `piTrainer/piTrainer/services/data/preview_service.py`
  - Adds deployed output/difference columns to the Records table column order.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Adds readable headers and numeric sorting/formatting for deployed output columns.
  - Adds helper sorting by largest steering/speed difference.
- `piTrainer/piTrainer/panels/data/image_preview_panel.py`
  - Shows model-vs-label comparison overlay when the selected row has deployed prediction output.
  - Adds deployed AI output to the metadata label.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.6 / piTrainer_0_9_6`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_6.md`
  - This patch note.

## Exact behavior changed

### New Data Workflow tab

The Data page now has:

1. `1 Load`
2. `2 Hide & Recover`
3. `3 Filter`
4. `4 Deploy`
5. `5 Review`

`4 Deploy` contains the new `Model Deploy` panel.

### Model deployment to visible frames

The user can now run model output on the currently visible Records rows using `Deploy Visible`.

Supported model sources:

- `Current trained model`
- `Load .keras / .h5 model`
- `Load .tflite model`

Helper buttons:

- `Browse`
- `Use Latest Keras`
- `Use Latest TFLite`

The deploy path reuses the existing validation/TFLite prediction code, so it follows the same image resizing, horizontal-flip handling, Keras output parsing, and TFLite output mapping used by the Validate and TFLite Check pages.

### New Records table columns after deploy

After deployment, visible frame rows can show:

- `AI Steering`
- `AI Speed`
- `Steer Diff`
- `Speed Diff`

The diff columns store absolute difference between the current label and deployed AI output.

### Sort by largest difference

The Model Deploy panel adds:

- `Sort Steer Diff`
- `Sort Speed Diff`

Both sort the Records table largest-first, so the most suspicious frame rows rise to the top.

The table also supports normal header sorting for these columns.

### Frame overlay comparison

When the selected Records row has deployed output, the Image Preview uses the existing prediction-comparison overlay:

- target/current label guide
- deployed AI output guide

This lets the user visually compare the saved label path against the model-predicted path on the frame.

### Apply deployed output to selected rows

The user can select rows with deployed output and use `Apply AI to Selected` after ticking `Confirm Apply`.

This overwrites both steering and speed labels for the selected rows using the deployed AI output, then writes the change through the existing JSONL update path. The selected rows' diff columns are refreshed to `0.000` after a successful apply because the saved label now matches the deployed output.

## Behavior intentionally not changed

- The `0.9.1` session working-folder behavior is preserved.
- The `0.9.1` playback FPS maximum of `250` is preserved.
- The `0.9.1` record-table alternating/selected-row readability is preserved.
- The `0.9.2` Hide & Recover workflow and hidden permanent-delete shortcut are preserved.
- The `0.9.3` and `0.9.4` wording cleanups are preserved.
- The `0.9.5` Image Preview Up/Down navigation focus fix is preserved.
- Existing Validate and TFLite Check pages are not replaced or removed.
- Training, preprocessing, export, and TFLite conversion behavior are not changed.
- Applying AI output still uses the existing metadata update safety path and asks for confirmation.

## Rollback-risk check

Built forward from the accepted v9 line by applying:

1. `piTrainer_0_9_0_.zip`
2. `piTrainer_0_9_1_patch.zip`
3. `piTrainer_0_9_2_patch.zip`
4. `piTrainer_0_9_3_patch.zip`
5. `piTrainer_0_9_4_patch.zip`
6. `piTrainer_0_9_5_patch.zip`
7. this `piTrainer_0_9_6` patch

Checked the current and previous relevant patch notes before finalising:

- `PATCH_NOTES_piTrainer_0_9_5.md`
- `PATCH_NOTES_piTrainer_0_9_4.md`
- `PATCH_NOTES_piTrainer_0_9_3.md`
- `PATCH_NOTES_piTrainer_0_9_2.md`

Confirmed this patch does not intentionally roll back the accepted behavior from `0.9.1` through `0.9.5`.

## Verification actually performed

- Applied `0.9.1`, `0.9.2`, `0.9.3`, `0.9.4`, and `0.9.5` over the uploaded `0.9.0` baseline before making this patch.
- Inspected existing Data page, Records table, Image Preview, validation service, TFLite service, and JSONL edit service before patching.
- Reused the existing validation/TFLite code path instead of creating a separate output parser.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Ran a local service-level smoke test using a fake Keras-like model and temporary JPEG frame to confirm:
  - deploy output rows are produced;
  - `pred_steering` / `pred_throttle` are added;
  - `steering_diff` / `speed_diff` are calculated.
- Verified the version file reports `0.9.6 / piTrainer_0_9_6`.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox.
- Real TensorFlow or TFLite inference with a real trained PiDrive model was not run in this sandbox.
- A PyInstaller / EXE rebuild was not run for this patch.

## Known limits / next steps

- `Deploy Visible` runs on the currently visible Records rows. Use filters first if only a subset should be deployed.
- Applying AI output overwrites steering and speed together for selected rows. A future patch could add separate apply buttons for steering-only or speed-only if needed.
- Prediction columns are in-memory review data. They are not written to session JSONL files unless the user uses `Apply AI to Selected`, which writes the model output into the normal steering/speed label fields.
