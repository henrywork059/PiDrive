# PATCH NOTES — CustomTrainer_0_2_14 (U27 YOLO model metadata and Pi preflight)

## Request
Add versioned, checksum-bound object-detection metadata to TFLite export and Pi deployment bundle, reject incompatible model families, retain old sidecar-free models through runtime tensor preflight, and protect the previous deployable bundle from failed rebuilds.

## Root cause
The export CLI and Pi bundle did not describe model purpose, class ordering, image dimensions or model checksum. Bundling deleted the previous `pi_bundle` before validating the next one. The Pi detection runtime immediately opened the camera without validating the model contract by synthetic inference.

## Files changed
- `CustomTrainer/custom_trainer/services/model_manifest.py` (new)
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/services/pi_deploy_service.py`
- `CustomTrainer/custom_trainer/assets/pi_runtime/run_tflite_detect.py`
- `CustomTrainer/custom_trainer/ui/main_window.py` — 0_2_14
- `CustomTrainer/tests/test_model_manifest.py` (new)
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_14.md` (new)

## Behavior
TFLite `cmd_export` publishes an adjacent typed YOLO sidecar describing RGB/NHWC image input, `zero_to_one` preprocessing, `yolo_boxes` interpretation, class names, quantization and SHA-256. Training seed is null when not available. Pi bundle verifies any source sidecar before copying, generates a bundle-specific checksum manifest and class list, assembles a complete staging folder, then swaps it in with backup/restore of the previous bundle on failure. It copies a standalone stdlib manifest reader alongside the runtime. On the Raspberry Pi, `run_tflite_detect.py` checks model kind/checksum/input shape/class names and invokes a zero-input synthetic inference before starting camera processing. Older sidecar-free models show a warning but require valid tensor geometry/inference; mismatched steering models are rejected. Existing Marking/Quick Deploy and other formats remain in place.

## Anti-rollback
Based on live GitHub CustomTrainer **0_2_13 draft PR #25**. Reviewed 0_2_13, 0_2_12, 0_2_11 and 0_2_10 patch notes. Preserves U18 session/duplicate aware YOLO splitting, U25 immutable dataset cache and its subprocess lease, compact Marking UI, class labels, export/validate pages and settings.

## Verification actually performed
- Package-local model manifest suite: **10/10 passed** against the same exact helper bytes published in GitHub.
- Locally compiled the manifest helper/tests. Inspected current GitHub export CLI, bundle builder and target Pi runtime; modified each from live branch code using unique source anchors.
- Actual Ultralytics export, physical Pi TFLite execution and GUI interactions were **not tested**. No claim of successful physical detection or benchmark is made.

## Limits / next steps
- A sidecar reports declared model semantics and is not a signed certificate. Synthetic preflight checks structural inference, not detection quality or class calibration.
- Existing model files without manifests remain supported with warnings; content-level near-duplicate or semantic mismatches cannot be inferred from tensor shape alone.
- Pi bundle rebuild may leave a recoverable staging/previous folder on unusual filesystem failures; no existing user configuration is reset.
- Review PR #25 first. No other component files are changed.
