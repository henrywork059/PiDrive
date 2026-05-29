# PATCH NOTES — piTrainer_0_8_6 Training Save Folder Browser Patch

## Request summary
- Build forward from the accepted V8 piTrainer patch line.
- In the Training tab, allow the user to browse and select the directory where `Save Trained Model` writes the trained `.keras` model.
- Keep the existing validation/export fixes from `0.8.1` through `0.8.5` intact.

## Cause / root cause
- The Training tab already had a `Save Trained Model` button, but it saved into the shared export output directory from `state.export_config.out_dir`.
- That meant the user had to change the Export page output folder or accept the default `trainer_out` folder even when saving directly from Training.
- There was no visible Training-tab folder field beside the save button, so the save destination was not clear or easy to change from the place where the action happens.

## Files changed
- `piTrainer/piTrainer/panels/train/train_control_panel.py`
  - Adds a `Trained model save folder` field to the Training Controls panel.
  - Adds a `Browse...` button that opens a directory chooser.
  - Persists the chosen folder in `QSettings` under `train/last_model_save_dir`.
  - Disables the folder field and browse button while training is running, then re-enables them after training stops.
- `piTrainer/piTrainer/pages/train_page.py`
  - Passes the current export output directory as the default save folder for first use.
  - Uses the Training-tab selected folder when saving a trained model.
  - Creates the selected folder if it does not already exist.
  - Reports a clear log/status message if the selected folder cannot be created or the model cannot be saved.
  - Keeps linking the saved `.keras` model back to the normal Validation page after a successful save.
- `piTrainer/piTrainer/app_state.py`
  - Adds `trained_model_out_dir` so the current session can record the directory used by the Training-tab save action.
- `piTrainer/piTrainer/version.py`
  - Updates the visible app version to `0.8.6` / `piTrainer_0_8_6`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_6.md`
  - This patch note.

## Exact behaviour changed
- In `3 Train > Training Workflow > 1 Setup > Training Controls`, the user can now see and edit:
  - `Trained model save folder`
- Clicking `Browse...` lets the user choose the folder used by `Save Trained Model`.
- Clicking `Save Trained Model` now writes to that selected Training-tab folder instead of silently using only the Export page output folder.
- The selected folder is remembered for later app sessions through Qt `QSettings`.
- If no Training save folder has been selected yet, the field defaults to the existing export output directory, preserving old behaviour for first use.
- Saved model filenames continue to use the export base name and the `_trained.keras` suffix.
- If a file with the same name already exists, the timestamp suffix behaviour is preserved.

## Behaviour intentionally not changed
- Training itself is unchanged.
- Dataset split logic, validation row source logic, export logic, TFLite ordered-output export, and Export Validation are unchanged.
- The Export page still controls the Export artifact directory for normal `.keras` / `.tflite` export.
- The Training save folder only changes the direct `Save Trained Model` action in the Training tab.
- The successful Training save still links the saved `.keras` path into the normal Validation page.
- No user data, datasets, runtime configs, saved models, or export artifacts are overwritten.

## Compatibility notes
- This is a patch-only zip for the V8 piTrainer line, intended to apply after `piTrainer_0_8_5_patch.zip`.
- The new save-folder setting is optional. Existing installs without the setting fall back to the export output directory.
- The setting is stored using the same Qt settings namespace already used elsewhere in piTrainer: `OpenAI` / `PiTrainer`.
- Because the visible app version is now `0.8.6`, any enabled online version-gate manifest must allow `0.8.6` before this patched app can open under release-control mode.

## Rollback-risk check
- Built forward from:
  - `piTrainer_0_8_0.zip`;
  - plus accepted `piTrainer_0_8_1_patch.zip`;
  - plus accepted `piTrainer_0_8_2_patch.zip`;
  - plus accepted `piTrainer_0_8_3_patch.zip`;
  - plus accepted `piTrainer_0_8_4_patch.zip`;
  - plus accepted `piTrainer_0_8_5_patch.zip`.
- Checked the latest and previous three relevant piTrainer patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_5.md`;
  - `PATCH_NOTES_piTrainer_0_8_4.md`;
  - `PATCH_NOTES_piTrainer_0_8_3.md`;
  - `PATCH_NOTES_piTrainer_0_8_2.md`.
- Confirmed this patch does not intentionally roll back:
  - Export-first tab layout from `0.8.1`;
  - Data page pandas warning fix from `0.8.2`;
  - Export Validation page and six-step workflow from `0.8.3`;
  - Data-page loaded-row validation and saved validation paths from `0.8.4`;
  - ordered single-output TFLite export from `0.8.5`;
  - generated-row hiding and edit redirection behavior;
  - horizontal-flip label safety;
  - version-gate code path.

## Verification actually performed
- Inspected the current V8 patch state after applying patches `0.8.1` through `0.8.5` on top of `piTrainer_0_8_0.zip`.
- Verified the real entry point remains `piTrainer/main.py`.
- Inspected the real Training page and Training Controls implementation before editing.
- Confirmed the save path used by `save_trained_model()` now comes from the Training Controls folder field.
- Confirmed the fallback is still the existing export output directory when the user has not selected a Training save folder.
- Confirmed the saved `.keras` path is still passed to the normal Validation page after saving.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static checks for the new `train/last_model_save_dir` settings key and the new `Trained model save folder` UI label.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI clicking was not run in this sandbox.
- Real TensorFlow/Keras model saving was not run because no trained in-memory model was available in this sandbox session.
- The online version-gate manifest was not checked or edited.

## Known limits / next steps
- The Training save-folder field controls only the direct `Save Trained Model` button.
- The Export page output directory remains separate so the user can keep training checkpoints/saved trained models and exported deployment artifacts in different folders.
