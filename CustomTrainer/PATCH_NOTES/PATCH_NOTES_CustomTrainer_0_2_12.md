# PATCH NOTES — CustomTrainer_0_2_12 (U18: YOLO split and label integrity)

## Request summary

Implement the next PiDrive engineering roadmap update **U18**: prevent training/validation contamination from same-session or byte-identical camera frames, detect invalid YOLO annotations before training, and report dataset quality per capture session. Preserve the accepted Marking quick-deploy and Export Validate UI.

## Baseline / anti-rollback

- Built forward directly from live GitHub CustomTrainer **0_2_11** on `main`, not an older 0_2_0 archive. Checked exact source blob hashes for each changed existing file against the uploaded PiDrive monorepo baseline before editing.
- Reviewed the latest CustomTrainer patch notes `0_2_11`, `0_2_10`, `0_2_9`, and `0_2_8`.
- Preserved the narrower Marking side panel and larger image preview from 0_2_11; Marking's model selector, selected-frame Quick Deploy, zero-box preservation, keyboard shortcuts, Export Validate page, and existing YOLO class IDs remain unchanged.
- This patch does **not** edit any `CustomTrainer/config` values, original image data, or manually saved source annotations.

## Root cause

1. `_split_image_paths` chose periodic indices from a sorted list and, for a singleton image, explicitly returned the same image in **both** training and validation sets. Two frames captured in the same session could cross partitions, inflating validation quality.
2. The training-cache path used the permissive Marking label parser. That parser clamps YOLO center/size values separately and ignores malformed rows, without checking that an entire box stays within normalized image boundaries. Invalid class identifiers and NaN/Infinity values were not comprehensively reported.
3. Preflight summaries were aggregate-only; operators lacked per-session invalid-label details before starting YOLO training or validation.

## Files changed

- `CustomTrainer/custom_trainer/services/dataset_service.py`
- `CustomTrainer/custom_trainer/services/yolo_io.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/pages/export_validate_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/tests/test_dataset_integrity.py` (new)
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_12.md` (new)

## Exact behavior changed

1. Automatic YOLO splits now assign **whole capture sessions** to one partition. A SHA-256 digest of each image finds exact duplicate bytes across sessions; those sessions are connected so identical content cannot appear in different partitions.
2. The split is deterministic and targets approximately 10% holdout *after* session grouping. No source path may appear in both training and validation. If there is just one independent group (including a singleton or fully duplicated sessions), `val.txt` is **empty**, never a copy of training data.
3. Train, Validate and Export Validate halt with a clear warning when their auto-prepared dataset has no independent validation holdout. Operators must supply a second independent recording session rather than accidentally report a fake validation score.
4. A new strict `validate_yolo_label_file` rejects and explains: noninteger/out-of-range class IDs; nonnumeric or nonfinite coordinates; centers outside [0,1]; zero/negative or oversized box dimensions; and full-box extents outside the image. Invalid rows are excluded **only from the generated YOLO training cache**. Valid rows in the same file remain usable.
5. The original `read_yolo_label_file` used by Marking is left intact to avoid changing manual annotation/canvas behavior. Source label files are not rewritten by strict validation; existing legacy-label migration is unchanged.
6. `DatasetSummary` now reports duplicate-image count, invalid files/rows, train/validation labeled counts, session-level metrics and up to 40 line-specific diagnostics. These details are logged before training and both validation tasks start; the existing `describe()` fields remain.
7. `has_usable_labels` now requires at least one valid annotation in the **training** partition, not merely anywhere in the dataset. Empty validation positives generate a warning.
8. The window version changes from 0_2_11 to **0_2_12**. No splitter changes, layout repositioning, or persistent UI-state reset.

## Verification actually performed

Using the uploaded GitHub-equivalent CustomTrainer baseline in a hardware-free environment:

- `PYTHONPATH=. python -m unittest discover -s tests -v` → **11 tests passed**.
- `python -m compileall -q custom_trainer run_custom_trainer.py tests` → passed.
- Verified that generated YOLO `dataset.yaml`, `train.txt`, `val.txt` and labels reflect session groups without train/validation duplication.
- Tests cover multiple session sizes, duplicate image bytes across sessions, singleton and one-session datasets, all-duplicate sessions, repeatable splitting, malformed/nonfinite/degenerate/out-of-bounds boxes, active class mapping, border-touching valid boxes, and unchanged source labels.
- All changed Python module and test Git blobs were compared against the exact locally tested copies before publishing.

## Known limits / next steps

- This patch implements **session-grouped holdouts**; an optional **sequence-block split with a temporal exclusion gap** remains a future UI-selectable fallback for users who truly cannot capture multiple independent sessions. Until then, a single-session dataset intentionally cannot launch training with a fabricated validation split.
- SHA-256 catches **byte-identical** images, not re-encoded or perceptually near-duplicate images. Adjacent frames in a single session are kept together but temporal/scene leakage across different sessions is not completely eliminated.
- The session split may exceed the approximate 10% target when a whole session is large. Content hashing adds I/O during dataset preparation.
- Existing dataset-cache deletion/rebuild while a reader is active is a separate issue (roadmap U25). This patch does not change cache lifecycle.
- The existing `sync_legacy_labels` migration can still copy old labels to canonical paths; this patch does not change that accepted behavior.
- Actual PySide6 UI workflows and Ultralytics model training/validation were **not executed** (PySide6 and YOLO are unavailable in the test runtime). Test those on the target workstation and inspect the validation session selection before merging.
