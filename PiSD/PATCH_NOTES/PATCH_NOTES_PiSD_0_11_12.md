# PATCH NOTES — PiSD_0_11_12 (U27 model compatibility and rollback)

## Request
Verify model purpose and checksum when metadata is available; preflight legacy/new steering TensorFlow Lite or Keras input/output contracts with a synthetic input; retain the last working model and saved selection on failed deployments. Preserve PiSD camera, AI correction and motor safety.

## Root cause
`AIDriveService.load_model` previously cleared active interpreter, selected model ID and persisted setting before the candidate loaded. Model-load failures therefore discarded a usable model. Generic TFLite input/output details could also admit an incompatible YOLO detector with no declared model family. The uploader did not accept/verify paired model metadata.

## Files changed
- `PiSD/pisd/core/model_manifest.py` (new)
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/app.py` — optional sidecar in upload request
- `PiSD/pisd/__init__.py` — version 0.11.12
- `PiSD/scripts/test_model_manifest.py` (new)
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_12.md` (new)

## Behavior
A present `<model filename>.manifest.json` must declare `steering_control` family, checksum matching the model file, RGB/NHWC geometry, zero-to-one normalization, and `steering_throttle` output. A missing sidecar is allowed with a legacy warning. A candidate model is constructed in isolation, its input/output tensor shape and quantization checked, and a zero synthetic inference executed before publishing the model selection. Invalid output shape/family, unsupported dtypes, non-finite output and invalid metadata fail without discarding the earlier active interpreter. Model changes while a preview/drive worker is running are refused until explicitly stopped. Keras candidates undergo analogous synthetic-output validation. Status surfaces manifest/warning, and uploads accept an optional `manifest` file that is verified against the uploaded bytes before publication. Deleting a model best-effort removes its sidecar. Existing API shapes are retained.

## Anti-rollback
Based on live GitHub PiSD **0.11.11 draft PR #26**, stacked on #22, #20 and #12. Reviewed notes 0.11.11, 0.11.10, 0.11.9 and 0.11.8. Preserves camera stale-frame latch, manual-drive failsafes, recording recovery, storage thresholds, AI correction modes, FPS controls, file IDs and persistent settings.

## Verification actually performed
- 10 manifest integrity/backward-compatibility tests passed in the PiSD package locally, using the exact Git blob published in this PR.
- Candidate loader changes applied to the actual current PR #26 implementation via exact single-occurrence source checks.
- The new candidate-loader integration, real TFLite/Keras runtimes, Flask upload API and Raspberry Pi hardware were **not tested** in the fully stacked branch. Test those before merge, with wheels raised and the prior known-good model selected.

## Known limits
- Synthetic model preflight verifies that the model runs structurally; it does not prove safe driving or predict correct steering. The existing independent motor/camera safeguards still apply.
- The original legacy two-scalar-output interpretation is retained; a sidecar-free model with the same tensor shapes but unrelated semantics may be impossible to distinguish. Existing settings are not reset on failure.
- Manifest/data uploads are separately published files and are not a cross-file filesystem transaction. A corrupt sidecar blocks load rather than silently ignoring it.
- Review/merge PR #26 before this change. No unrelated component touched.
