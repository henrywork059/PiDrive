# PATCH NOTES — piTrainer_0_9_10 Deploy Navigation and Merge-Speed Fix

## Request summary

Fix two issues reported after deploying model output onto the Data Records table:

- Up/Down next-frame navigation stopped working after model deploy unless the Records table was clicked again.
- Model deployment felt unexpectedly slow.

## Cause / root cause

The navigation issue was focus-related. After clicking Deploy or the diff-sort buttons, keyboard focus stayed on the deploy controls. The Records table owns the normal Up/Down row-cycling shortcut, so plain arrow-key presses were no longer reaching the table.

The deploy slowness was partly caused by how predictions were merged back into the loaded DataFrames. The previous deploy merge updated each predicted row field-by-field and repeatedly rebuilt a full row mask across `dataset_df`, `filtered_df`, and the current preview source. On larger sessions this created avoidable repeated DataFrame scans after prediction completed.

## Files changed

- `piTrainer/piTrainer/pages/data_page.py`
  - Adds a visible status message before deploy starts, including the target row count.
  - Replaces row-by-row prediction-field merging with a bulk identity-map merge for deployed output fields.
  - Restores Records-table keyboard focus after deploy, diff sort, and Apply AI output.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Adds `focus_table_for_keyboard()` so external Data Workflow buttons can return focus to the Records table.
  - Keeps the current row anchored to the first column before refocusing.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.10 / piTrainer_0_9_10`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_10.md`
  - This patch note.

## Exact behavior changed

- After running Deploy Visible, pressing Up/Down should move to the previous/next frame immediately.
- After sorting by steering difference or speed difference, pressing Up/Down should also continue to cycle frames immediately.
- After applying deployed AI output to selected frames, the Records table regains keyboard focus.
- Deploy now shows a status message such as `Deploying model to 500 visible frame(s)...` before prediction work starts.
- Prediction values are merged into the table source in one pass per DataFrame instead of repeatedly scanning the full dataset for every predicted row and every deployed field.

## Behavior intentionally not changed

- The `5 Deploy` workflow tab remains in place.
- The Data Workflow order remains `1 Load`, `2 Hide & Recover`, `3 Filter`, `4 Review`, `5 Deploy`.
- The deployed output columns are unchanged: `AI Steering`, `AI Speed`, `Steer Diff`, and `Speed Diff`.
- Existing deploy source options are unchanged: current trained model, `.keras` / `.h5`, and `.tflite`.
- The model prediction logic is still shared with the existing Validate/TFLite Check paths.
- The `0.9.9` Preprocess status banner and default source/mode changes are preserved.
- The `0.9.8` deploy-file packaging repair is preserved.
- The `0.9.7` tab-order correction is preserved.
- The `0.9.5` image-preview Up/Down navigation fix is preserved.

## Rollback-risk check

Checked the latest current code state and the previous v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_9.md`
- `PATCH_NOTES_piTrainer_0_9_8.md`
- `PATCH_NOTES_piTrainer_0_9_7.md`

This patch builds forward from `0.9.9` and does not roll back the recent Preprocess, Deploy, tab-order, or packaging fixes.

## Verification actually performed

- Built this patch on top of the accepted `0.9.9` working state.
- Inspected the current Data page, deploy panel, deploy service, Records preview panel, and image-preview navigation code before patching.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Ran a local pandas micro-check of the new prediction-map merge path on 5,000 fake rows; all prediction columns were populated and the merge completed quickly in the sandbox.
- Verified the version file reports `0.9.10 / piTrainer_0_9_10`.
- Prepared a patch-only zip with only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox.
- Real TensorFlow/Keras or TFLite model deployment was not run in this sandbox.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- The prediction step itself still depends on model type, image count, image size, and whether the TFLite model supports batching. Very large visible tables can still take time to predict. Use `Max rows` for a quick sample deploy, or filter the table before deploying when testing.
- This patch speeds the post-prediction merge/update path and fixes keyboard focus after deploy; it does not add a background worker/progress bar for long-running prediction yet.
