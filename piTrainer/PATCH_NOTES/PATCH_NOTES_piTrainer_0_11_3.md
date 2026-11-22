# PATCH NOTES — piTrainer_0_11_3 (U27 model manifest exports)

## Request
Attach backward-compatible checksum-bound steering-model metadata to exported Keras and TensorFlow Lite artifacts. Preserve non-overwriting export, train/validation data selection, and the existing seed/geometry settings.

## Root cause
Exports previously contained the neural-network bytes but no stable machine-readable description of the steering model family, RGB input normalization, output interpretation or training seed. Runtime model-shape inspection alone cannot detect an unrelated model with compatible tensor sizes or a modified artifact.

## Files changed
- `piTrainer/piTrainer/utils/model_manifest.py` — common schema/version/checksum and atomic sidecar writer (new)
- `piTrainer/piTrainer/services/export/export_service.py` — emit manifest after successful artifact creation
- `piTrainer/piTrainer/version.py` — 0.11.3
- `piTrainer/tests/test_model_manifest.py` — 10 manifest tests (new)
- `piTrainer/tests/test_export_manifest.py` — 3 exporter integration tests (new)
- `piTrainer/README.md`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_3.md` (new)

## Behavior
Every normal `export_model_artifacts` output now receives `<filename>.manifest.json` with `schema_version:1`, model_kind `steering_control`, SHA-256 of the actual model bytes, NHWC RGB width/height/channels, `zero_to_one` normalization, output `steering_throttle`, quantization mode and explicit training seed. A quantization-optimized TFLite export is labeled `dynamic` because it retains float32 I/O. `.keras` exports use float32. Manifest files are staged and atomically renamed; a manifest failure is raised rather than reporting successful deployment. Old artifact naming and non-overwrite behavior are untouched; no user model or dataset is rewritten by this code patch.

## Anti-rollback
Based on live GitHub piTrainer **0.11.2 draft PR #17**. Reviewed current and previous component patch notes 0.11.2, 0.11.1, 0.11.0 and 0.10.6. Preserves U11 source-safe grouping, U15 collision-free preprocess saves, U17 atomic label editing, PySide6 page layout/docking and exports.

## Verification actually performed
- `PYTHONPATH=. python -m unittest discover -s tests -p test_model_manifest.py -q`: **10 passed** on the package-local manifest implementation.
- `PYTHONPATH=. python -m unittest discover -s tests -p test_export_manifest.py -q`: **3 passed** using TensorFlow-free export mocks in the uploaded baseline.
- Python compilation of the locally exercised export/manifest/test modules: passed.
- Exact Git blob hashes of new manifest/test files matched the locally tested sources. The export method patch was applied to the current PR #17 source using unique anchors.

## Limits / next steps
- Real TensorFlow model conversion and Windows GUI deployment were not run; validate on the target workstation.
- A partial artifact can remain on disk if manifest publication fails; the UI reports failure. The sidecar is not cryptographically signed: SHA-256 detects mismatches but does not authenticate the exporter. Transfer model and manifest together.
- Merge/review PR #17 before this stacked PR. No ZIP or full project package was created.
