# PATCH NOTES — piTrainer_0_8_15 Reliability-First Packaging Patch

## Request summary
- Stop using aggressive EXE size-reduction exclusions for piTrainer packaging.
- Package from the current working Python environment as reliably as possible.
- Keep one-folder packaging because TensorFlow/Keras/PySide are large and `--onefile` is slower and less reliable.

## Cause / root cause
- Earlier packaging work tried to reduce the output size by excluding modules that looked unnecessary.
- That caused real frozen-app failures because some dependencies import modules indirectly or dynamically:
  - Matplotlib / pyparsing needed `unittest` during startup.
  - TensorFlow/Keras can import training/backend modules only when `Start Training` is pressed.
- The user confirmed the correct priority: reliability over a smaller package. Most of the size comes from TensorFlow/Keras, so excluding small or uncertain modules is not worth breaking training.

## Files changed
- `piTrainer/PACKAGING/piTrainer_onedir.spec`
  - Removes the aggressive exclusion list.
  - Keeps `excludes = []` so PyInstaller and its hooks can collect what the current environment needs.
  - Keeps the existing one-folder build, TensorFlow/Keras hidden imports, metadata collection, and runtime hook behavior.
- `piTrainer/PACKAGING/README_WINDOWS_EXE.md`
  - Updates packaging guidance to explain the reliability-first strategy.
  - Removes the older advice that the spec excludes common packages to reduce size.
  - Clarifies that TensorFlow/Keras dominate the size and that training reliability is more important than a smaller folder.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.8.15` / `piTrainer_0_8_15`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_15.md`
  - This patch note.

## Exact behavior changed
- PyInstaller packaging no longer excludes standard-library modules, TensorFlow/Keras internals, Matplotlib internals, or optional dependency names through the spec exclusion list.
- The build remains a one-folder EXE build:
  - `dist_exe/PiTrainer/PiTrainer.exe`
  - runtime libraries inside `dist_exe/PiTrainer/_internal`
  - optional transfer zip at `dist_exe/PiTrainer_win_onedir.zip`
- The output folder may become larger, but it should be less likely to open successfully and then fail during training because a dynamically imported module was excluded.

## Behavior intentionally not changed
- No piTrainer runtime logic was changed.
- No training algorithm, dataset loading, export, validation, or TFLite output code was changed.
- The build still uses one-folder mode, not one-file mode.
- The existing build retry behavior for the final zip remains unchanged.
- The existing TensorFlow/Keras runtime hook remains unchanged.

## Compatibility notes
- This is a patch-only zip for the V8 piTrainer line, intended to apply after `piTrainer_0_8_14_packaging_training_diagnostics_patch.zip`.
- The output app folder may be larger than earlier packaging attempts.
- A larger folder is expected and acceptable because TensorFlow/Keras are required for training and export.
- Because the visible app version is now `0.8.15`, any enabled online version-gate manifest must allow `0.8.15` before this patched app can open under release-control mode.

## Rollback-risk check
- Built forward from the available latest packaging state through `0.8.14`.
- Checked the latest and previous relevant packaging patch notes available in this session:
  - `PATCH_NOTES_piTrainer_0_8_14.md`
  - `PATCH_NOTES_piTrainer_0_8_13.md`
  - `PATCH_NOTES_piTrainer_0_8_12.md`
  - `PATCH_NOTES_piTrainer_0_8_11.md`
- Confirmed this patch does not intentionally roll back:
  - corrected `piTrainer/main.py` entry point from `0.8.10`;
  - zip retry/fallback behavior from `0.8.11`;
  - `unittest` startup fix from `0.8.12`;
  - TensorFlow/Keras backend runtime hook from `0.8.13`;
  - training diagnostic worker changes from `0.8.14`.

## Verification actually performed
- Inspected the current packaging spec from the reconstructed latest packaging patch state.
- Confirmed the old exclusion list was replaced with `excludes = []`.
- Confirmed the README no longer tells the user that the spec excludes packages to reduce size.
- Parsed the patched Python spec/version files for syntax successfully.
- Confirmed the patch package contains only changed files plus this patch note.

## Verification not performed
- A real Windows PyInstaller build was not run in this Linux sandbox.
- Packaged EXE training was not tested here because the Windows environment, TensorFlow runtime, and user dataset are on the user's PC.

## Known limits / next steps
- Rebuild the one-folder EXE after applying this patch.
- The build may take longer and the output folder may be larger.
- If training still fails after this reliability-first build, use the `0.8.14+` training diagnostic log to capture the exact runtime traceback.
