# PATCH NOTES — PiServer_0_4_17 (U27 model manifest preflight)

## Request
Add sidecar checksum/family/geometry validation and safe model upload/deletion without losing existing TFLite preflight or accepted PiServer safety/security behavior.

## Root cause
Existing PiServer dynamic tensor signature checks accept models with matching input/output dimensions but no declared purpose or checksum. The upload endpoint could replace a file with an existing name, possibly an active/interpreter-backed model, without staging a matching metadata contract.

## Files changed
- `PiServer/piserver/core/model_manifest.py` (new)
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/app.py` (APP_VERSION 0_4_17)
- `PiServer/tests/test_model_manifest.py` (new)
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_17.md` (new)

## Behavior
A supplied `<model>.tflite.manifest.json` declares `steering_control`, SHA-256, RGB/NHWC input dimensions/normalization, ordered steering/throttle outputs, quantization and training seed. The loader checks the manifest before interpreter construction, validates manifest geometry against actual tensor geometry, and retains U12's zero-input TFLite preflight. Only on successful preflight does the active interpreter, model name and metadata switch; any failure preserves the previous active model. Sidecar-free old TFLite files still load with a warning and shape/inference checks. `model_metadata` appears in protected list/load responses. Upload accepts optional paired multipart `manifest` and rejects a wrong family/checksum. An existing model filename cannot be overwritten. Deleting a model removes its matching sidecar after deleting the model; failed deletion retains active interpreter. Previously accepted manual watchdog and LAN protections are unchanged.

## Anti-rollback
Built forward on live GitHub **PiServer 0_4_16 draft PR #27**, stacked on #23, #16, #15, #14 and #9. Reviewed current/previous notes 0_4_16, 0_4_15, 0_4_14 and 0_4_13. Preserves cross-process hardware owner lease, TFLite dynamic geometry, LAN access token/CSRF, storage guard, latency metrics, manual timeout stop and UI.

## Verification actually performed
- New independent stdlib manifest tests: **10/10 passed** on the package-local helper (exact Git blob verified).
- Prior 0_4_13 model-compatibility tests remain unchanged, but the full stacked runtime/Flask suite was **not rerun** for this patch. Current service/app source was edited through exact source anchors with no unrelated file changes.
- Real Pi 4, GPIO/camera and full model inference performance were not tested.

## Known limits
- A SHA-256 checksum detects bytes mismatching the supplied sidecar, but does not prove publisher authenticity; a malicious model and maliciously matching sidecar are not prevented.
- A model upload with optional sidecar is best-effort published as two files, not an atomic cross-file transaction. Existing/active files are not overwritten.
- Tensor-shape preflight cannot recognize semantic mismatches in old sidecar-free models. Full hardware validation remains required before merge.
- Review/merge PR #27 first. No unrelated files changed.
