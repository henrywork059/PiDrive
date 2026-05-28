# PATCH NOTES — piTrainer_0_8_4 Validation Loaded-Rows + Last-Used Model Paths Patch

## Request summary
- Build forward from the accepted V8 piTrainer patch line.
- Fix the Export Validation page showing `No rows available`.
- Stop requiring a fresh train/split step before validation.
- Make both normal Validation and Export Validation validate against the data already loaded on the Data page.
- Make the validation model file pickers remember the last-used folder/path instead of opening the default export folder every time.

## Cause / root cause
- In `0.8.3`, both validation pages still defaulted to `Validation split` as their dataset source.
- `state.val_df` and `state.train_df` are empty immediately after loading data because they are only filled after preparing/training a split.
- Therefore, validation could incorrectly show no available rows even though the Data page already had usable loaded rows in `state.filtered_df`.
- The normal Validation page also defaulted to `Current trained model`, so after restarting the app or after loading data without training in the current run, it appeared that the user had to train every time.
- Validation model file dialogs used `state.export_config.out_dir` as the initial folder and did not persist the last selected model/TFLite directory through `QSettings`.

## Files changed
- `piTrainer/piTrainer/pages/validation_page.py`
  - Adds a Data-page loaded-row dataset helper.
  - Defaults validation data selection to loaded Data page rows.
  - Falls back to Data page loaded rows if a selected split is empty.
  - Updates the empty-row status message to tell the user to load sessions on the Data page.
- `piTrainer/piTrainer/pages/export_validation_page.py`
  - Adds the same loaded-row selection behavior for exported TFLite validation.
  - Falls back to Data page loaded rows if selected split rows are empty.
  - Updates the empty-row status message.
- `piTrainer/piTrainer/panels/validation/validation_config_panel.py`
  - Changes dataset source order to make `Data page loaded rows` the first/default choice.
  - Restores the last selected `.keras` / `.h5` path from `QSettings`.
  - Opens the file picker in the last selected model folder when available.
  - Saves selected model path/folder back to `QSettings`.
  - Switches automatically to `Load .keras / .h5 model` when a saved/restored model path exists.
- `piTrainer/piTrainer/panels/export_validation/export_validation_config_panel.py`
  - Changes dataset source order to make `Data page loaded rows` the first/default choice.
  - Restores the last selected `.tflite` path from `QSettings`.
  - Opens the file picker in the last selected TFLite folder when available.
  - Saves selected TFLite path/folder back to `QSettings`.
  - Avoids treating an empty path as the current working directory.
- `piTrainer/piTrainer/panels/validation/validation_summary_panel.py`
  - Shows loaded Data page row count instead of the older filtered label.
- `piTrainer/piTrainer/panels/export_validation/export_validation_summary_panel.py`
  - Shows loaded Data page row count instead of the older filtered label.
- `piTrainer/piTrainer/pages/export_page.py`
  - When Export creates a `.keras` / `.h5` artifact, links it to the normal Validation page and persists it through the Validation config panel.
  - Keeps the existing TFLite link to Export Validation.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.8.4` / `piTrainer_0_8_4`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_4.md`
  - This patch note.

## Exact behaviour changed
- `4 Validate` now uses `Data page loaded rows` by default.
- `6 Export Validation` now uses `Data page loaded rows` by default.
- After loading sessions in `1 Data`, validation can run on those loaded rows without first preparing a split or training again.
- If the user manually selects `Validation split` or `Training split` but that split is empty, the page falls back to the loaded Data page rows instead of immediately showing no rows.
- Normal Validation remembers the last `.keras` / `.h5` file path and directory.
- Export Validation remembers the last `.tflite` file path and directory.
- Browsing for a validation model opens from the last used validation-model folder when possible.
- Browsing for a TFLite model opens from the last used TFLite folder when possible.
- If Export creates a Keras model artifact, it is automatically linked into `4 Validate` as the external model path.
- If Export creates a TFLite artifact, it remains automatically linked into `6 Export Validation`.

## Behaviour intentionally not changed
- The `0.8.1` Export page remains action-first:
  - `1 Export`
  - `2 Status`
- The `0.8.2` Data page pandas warning fix remains in place.
- The `0.8.3` Export Validation page remains as tab `6 Export Validation` and still uses a real TFLite interpreter.
- Training, preprocessing, Data page loading, generated-row hiding, edit redirection, and overlay display behavior are not rewritten.
- User dataset/runtime files are not reset or overwritten.
- The user can still manually validate only the training split or validation split when those split rows exist.

## Compatibility notes
- This is a patch-only zip for the V8 piTrainer line, intended to apply after `piTrainer_0_8_3_patch.zip`.
- The validation path storage uses the existing Qt `QSettings('OpenAI', 'PiTrainer')` mechanism already used by the Data page records root and dock layout state.
- Because the visible app version is now `0.8.4`, any enabled online version-gate manifest must allow `0.8.4` before this patched app can open under release-control mode.

## Rollback-risk check
- Built forward from:
  - `piTrainer_0_8_0.zip`
  - plus accepted `piTrainer_0_8_1_patch.zip`
  - plus accepted `piTrainer_0_8_2_patch.zip`
  - plus accepted `piTrainer_0_8_3_patch.zip`
- Checked the latest and previous three relevant piTrainer patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_3.md`
  - `PATCH_NOTES_piTrainer_0_8_2.md`
  - `PATCH_NOTES_piTrainer_0_8_1.md`
  - `PATCH_NOTES_piTrainer_0_8_0.md`
- Confirmed this patch does not intentionally roll back:
  - Export-first tab layout from `0.8.1`;
  - Data page pandas warning fix from `0.8.2`;
  - Export Validation page and six-step workflow from `0.8.3`;
  - generated-data hiding and edit redirection behavior;
  - horizontal-flip label safety;
  - version-gate code path.

## Verification actually performed
- Inspected the real current v8 patch state after applying `0.8.1`, `0.8.2`, and `0.8.3` on top of `piTrainer_0_8_0.zip`.
- Confirmed the reported issue matched the previous default source of `Validation split` / empty split data.
- Confirmed both validation config panels now put `Data page loaded rows` first.
- Confirmed both validation pages now read loaded Data page rows from `state.filtered_df`, with `state.dataset_df` as fallback.
- Confirmed both validation pages fall back to loaded rows when selected split rows are empty.
- Confirmed validation model path persistence keys are written through `QSettings`.
- Confirmed Export still links `.tflite` to Export Validation and now also links `.keras` / `.h5` artifacts to normal Validation.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static checks for the new loaded-row source labels, path persistence keys, and empty-path guard.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI clicking was not run in this sandbox.
- Real TensorFlow/Keras validation was not run because no saved model and loaded dataset were provided in the sandbox.
- Real TFLite validation was not run because no exported `.tflite` model and image dataset were provided in the sandbox.
- The online version-gate manifest was not checked or edited.

## Known limits / next steps
- This patch fixes validation row source selection and last-used model directories.
- If Export Validation now shows a narrow TFLite output range while normal Validation looks correct on the same Data page rows, the next likely issue is the TFLite export/output mapping or TFLite interpreter preprocessing.
- If Export Validation looks correct but the car still shows narrow outputs, the next likely issue is the Pi/car-side TFLite input normalization or output parsing path.
