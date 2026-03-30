# PATCH NOTES — CustomTrainer 0_2_2

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_1** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Fix the new issue where Training/Validation ran on GPU but still behaved like the dataset had no labels, producing zero detections, zero metrics, and repeated `No labels found` warnings even though the user had saved label files in CustomTrainer.

## Problems addressed
1. Training and validation could run successfully on the GPU while still seeing **zero usable labels**.
2. Flat session folders such as `snapshots/*.jpg` with labels in `snapshots/labels/*.txt` were not being exported in a structure that Ultralytics reliably maps to detection labels.
3. The app could still launch long training/validation jobs even when the dataset contained **zero usable YOLO boxes**, wasting time and producing misleading zero-metric runs.

## Likely root cause
- CustomTrainer saved labels under a canonical `labels/` folder inside the sessions root, which was fine for the marking workflow.
- However, the generated `dataset.yaml` referenced the original image paths directly, and for flat session layouts those image paths did **not** live under an `images/` directory.
- Ultralytics' label discovery is strongly tied to YOLO-style image/label path conventions, so the generated dataset looked like an all-background dataset even though label files existed.
- Because there was no dataset preflight check, Training/Validation could continue and only show the failure indirectly in the Ultralytics logs.

## Changes made

### 1) Rebuilt dataset export around a YOLO-compatible cache bundle
- Reworked `custom_trainer/services/dataset_service.py` to build a fresh dataset cache under:
  - `sessions_root/.customtrainer_yolo_cache/images/...`
  - `sessions_root/.customtrainer_yolo_cache/labels/...`
- Images are linked into the cache with a hard-link when possible and copied only as a fallback.
- Labels are normalized through CustomTrainer's YOLO parser/writer before being written into the cache.
- The generated `dataset.yaml` now points to this cache bundle, so Ultralytics sees a standard `images/` + `labels/` structure.

### 2) Added dataset summary / preflight reporting
- Added a dataset summary object that tracks:
  - total images
  - train / val split counts
  - labeled image count
  - total YOLO box instances
  - empty / missing label count
  - invalid label file count
  - migrated legacy label count
- Training and Validation now log this summary before they launch.

### 3) Blocked empty-label runs early
- Training now refreshes the current sessions-root dataset before launch and stops with a clear UI error if there are **no usable YOLO boxes**.
- Validation now does the same instead of letting Ultralytics run and only later report all-zero metrics.
- This prevents the misleading "successful" empty training runs seen in the user's log.

### 4) Preserved recent accepted fixes
- Kept the 0_2_1 isolated Torch/CUDA probing behavior so this patch does **not** reintroduce the Windows startup crash.
- Updated the main window title to **CustomTrainer 0_2_2**.
- Updated the README summary to describe the new dataset-cache and preflight behavior.

## Files changed
- `CustomTrainer/custom_trainer/services/dataset_service.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_2.md`

## Verification performed
- Reviewed the user's training log showing:
  - GPU detected and used successfully
  - repeated `No labels found` / `Labels are missing or empty` warnings
  - all-zero validation metrics and no detections
- Verified that the previous patch's startup-safe device probing remains intact.
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Ran a local dataset-bundle smoke test in the container on a synthetic flat session layout (`session/*.jpg` + `session/labels/*.txt`) and confirmed:
  - `dataset.yaml` is generated
  - the YOLO cache is created under `.customtrainer_yolo_cache`
  - train/val lists point to cached images under an `images/` directory
  - parsed label statistics report non-zero instances when valid labels are present

## Known limits / next steps
- This patch prevents empty-label training/validation from silently running, but it does not invent labels for frames that are truly unlabeled.
- If label files contain malformed lines or out-of-range class IDs, those files may still be counted as invalid and excluded from the usable-instance count.
- A later patch could add a dedicated **Dataset Diagnostics** panel to show which specific files are empty or malformed before training.
