# CustomTrainer 0_1_12 Patch Notes

## Summary
This patch changes the Validation preview so it can show the model’s boxed prediction result instead of only mirroring the raw source image.

## Main changes

### 1) Prediction preview now shows the deployed model output
- The Validation page now listens for prediction output markers from the Ultralytics runner.
- After **Run Prediction**, the preview panel switches from the raw source image to the annotated image saved by the model.
- The preview info panel also shows a short summary of detected boxes.

### 2) Prediction runs now save to a session-oriented runs folder
- Validation and prediction commands now pass explicit `project` and `name` values.
- This keeps outputs grouped under the current sessions root `runs/detect/...` path instead of mixing them into a generic default location.

### 3) Validation / prediction logging is cleaner
- Removed the giant raw object / array dumps from `val` and `predict` command output.
- Validation now emits a concise metrics summary line.
- Prediction now emits concise box summary lines and the saved preview-image path.

### 4) Version / docs updated
- Main window title updated to `CustomTrainer 0_1_12`.
- README updated to explain that Run Prediction refreshes the preview with the boxed model result.

## Files changed
- `CustomTrainer/custom_trainer/services/ultralytics_runner.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/state.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_12.md`

## Verification
- Python syntax check passed for the changed Python files.
- Full GUI runtime testing was not possible here because the desktop PySide6 environment is not available in this container.

## Notes
- This is a patch-only zip. Extract it over your current `CustomTrainer` project.
- To see the boxed preview, choose weights + an image source, then click **Run Prediction**.
