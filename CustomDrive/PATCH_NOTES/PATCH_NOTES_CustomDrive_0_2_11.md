# PATCH NOTES — CustomDrive_0_2_11

## Request summary
Make sure the AI model can deploy to the live preview overlay in CustomDrive.

## Root cause
The GUI already had AI upload/deploy controls and a preview overlay path, but the detector loader still had two practical compatibility gaps:

1. It mainly expected same-stem sidecar files like `best_float32.txt` and `best_float32.json`.
2. Output parsing could choose the wrong orientation when labels were missing, which could break object detection models that were uploaded without a matching labels file.

That made the live preview deployment path fragile, especially for models exported from CustomTrainer.

## Files changed
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/templates/index.html`

## Exact behavior changed
### 1) CustomTrainer bundle compatibility added
The detector loader now accepts both:
- same-stem sidecars:
  - `best_float32.tflite`
  - `best_float32.txt`
  - `best_float32.json`
- CustomTrainer Pi bundle sidecars:
  - `best_float32.tflite`
  - `labels.txt`
  - `model_config.json`

If `model_config.json` declares `model_filename` matching the selected model, CustomDrive now uses that config and the declared `labels_filename` for deployment.

### 2) More robust output parsing
The prediction parser now infers the feature/output orientation more safely even when labels are missing, instead of relying too heavily on `num_classes` from the label count.

This reduces the chance that a valid object-detection model deploys successfully but shows no overlay because the output matrix was interpreted in the wrong direction.

### 3) Preview refresh after AI changes
The GUI now refreshes the live preview stream after:
- model upload
- model deploy
- AI config save

This makes the deployed overlay show up on the preview more reliably without needing a manual browser refresh.

### 4) AI settings help text updated
The AI settings panel now explicitly says that CustomTrainer bundle files are accepted.

## Verification performed
- Reconstructed the latest accepted CustomDrive state from the `CustomDrive_0_2_0` baseline plus later accepted patches up to `0_2_10` before editing, to avoid rolling back the working arm-control changes.
- Ran `python -m compileall CustomDrive`.
- Ran a local code-level check confirming that the new loader resolves:
  - `model_config.json`
  - `labels.txt`
  - the matching `model_filename`
  for a CustomTrainer-style bundle.

## Known limits / next steps
- I could not run real TFLite inference in this container because neither `tflite_runtime` nor TensorFlow Lite is installed here.
- This patch improves the deployment path and compatibility, but the final end-to-end confirmation of live detection overlay still needs your Pi runtime with the actual model installed.
