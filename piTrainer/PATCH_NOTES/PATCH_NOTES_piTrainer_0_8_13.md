# piTrainer 0.8.13 Patch Notes

## Request summary

The packaged one-folder EXE can now open, but training fails inside the frozen app. The build log still completes successfully, so the issue is likely runtime packaging for TensorFlow/Keras training modules rather than the EXE build itself.

## Cause / likely cause

PyInstaller can build and launch the UI while still missing modules that are only imported later when the Train page starts TensorFlow/Keras training.

The build log shows the EXE build completed and produced the launcher/zip, so this patch focuses on the frozen training runtime rather than the build step. It also shows PyInstaller processing TensorFlow/Keras hooks and warning about optional backends such as torch, which are not used by piTrainer training.

## Files changed

- `piTrainer/PACKAGING/piTrainer_onedir.spec`
- `piTrainer/PACKAGING/build_windows_onedir.ps1`
- `piTrainer/PACKAGING/rthook_pitrainer_training_env.py`
- `piTrainer/PACKAGING/README_WINDOWS_EXE.md`
- `piTrainer/piTrainer/version.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_8_13.md`

## Exact behavior changed

- Adds a PyInstaller runtime hook that runs before the frozen app imports TensorFlow/Keras.
- Pins Keras to the TensorFlow backend in the frozen app:
  - `KERAS_BACKEND=tensorflow`
- Disables oneDNN graph rewrites in the frozen app:
  - `TF_ENABLE_ONEDNN_OPTS=0`
- Keeps TensorFlow runtime logging quieter:
  - `TF_CPP_MIN_LOG_LEVEL=2`
- Keeps Matplotlib on the Qt backend:
  - `MPLBACKEND=QtAgg`
- Adds explicit hidden imports for TensorFlow/Keras modules used by the Train page, including layers, callbacks, optimizers, losses, saving, and TensorFlow-backed Keras internals.
- Adds focused `collect_submodules(...)` calls for the TensorFlow Keras backend and Keras training-related packages.
- Excludes optional unused Keras torch/jax backend modules so the app stays on TensorFlow and avoids optional-backend probing in the frozen EXE.
- Updates packaging README troubleshooting notes for EXE training failures.
- Updates the displayed version to `0.8.13 / piTrainer_0_8_13`.

## Behavior intentionally not changed

- Training code and model architecture are not changed.
- Dataset loading and preprocessing are not changed.
- Export Validation and TFLite output ordering are not changed.
- EXE build remains one-folder, not one-file, to keep startup easier and faster.
- The `0.8.12` unittest packaging fix is preserved.
- The `0.8.11` zip retry behavior is preserved.
- The `0.8.10` entry-point spec fix is preserved.

## Compatibility / rollback safety

- This is a packaging-only runtime fix for the EXE training path.
- It does not affect normal `python main.py` use.
- It builds forward from `0.8.12` and keeps earlier accepted packaging/runtime fixes.
- The frozen EXE may become slightly larger because more Keras training modules are explicitly included, but this is necessary for the Train page to work from the packaged app.

## Verification performed

- Inspected the current packaging spec and build script after applying the accepted packaging patch sequence through `0.8.12`.
- Checked the latest and previous relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_8_12.md`
  - `PATCH_NOTES_piTrainer_0_8_11.md`
  - `PATCH_NOTES_piTrainer_0_8_10.md`
  - `PATCH_NOTES_piTrainer_0_8_9.md`
- Verified the spec still points to the real entry point:
  - `piTrainer/main.py`
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Verified the new runtime hook file exists and is registered by the spec.
- Verified the spec includes the new TensorFlow/Keras training hidden imports.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed

- Live Windows/PySide6 GUI clicking was not run in this sandbox.
- Real PyInstaller build was not run in this Linux sandbox.
- Real EXE training was not run because that requires the user's Windows built folder and loaded training data.
- The exact runtime traceback from the failed training attempt was not included in the pasted log, so this patch targets the most likely frozen TensorFlow/Keras training-module cause.

## Known limits / next steps

- Apply this patch, rebuild the EXE, then try Train again.
- If training still fails, rebuild with the console switch and paste the Train page log plus console traceback:

```powershell
powershell -ExecutionPolicy Bypass -File .\PACKAGING\build_windows_onedir.ps1 -Console
.\dist_exe\PiTrainer\PiTrainer.exe
```
