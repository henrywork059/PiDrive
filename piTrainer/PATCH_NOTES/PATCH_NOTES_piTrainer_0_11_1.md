# PATCH NOTES — piTrainer_0_11_1 Source-Safe Train/Validation and Preprocess Saves

## Request summary
Implement roadmap items **U11** (prevent train/validation leakage caused by synthetic variants of source frames) and **U15** (avoid overwriting preprocessed datasets saved multiple times in one second).

## Baseline and anti-rollback
Built on the current GitHub piTrainer 0.11.0 stable baseline. Compared the live source with the uploaded piTrainer_0_11_0.zip baseline and reviewed the latest V11 note and preceding V10 notes for 0.10.6, 0.10.5, 0.10.4 and 0.10.3. Existing model non-overwrite saves, Data sorting, Session Source selection/resize, docking, Validate/TFLite review, data editing and exporting remain unchanged.

## Root cause
- Preprocessing creates rows with distinct synthetic frame IDs and a shared source_frame_id (often also the same abs_image), but the Train page's Random rows and Sequential rows split treated them as independent examples.
- save_preprocessed_dataset previously used a timestamped directory name with only second precision and ensure_dir(...), reusing that directory on a collision and overwriting CSV, JSONL and recipe.

## Files changed
- piTrainer/piTrainer/services/train/split_service.py
- piTrainer/piTrainer/services/preprocess/preprocess_service.py
- piTrainer/piTrainer/version.py
- piTrainer/tests/test_dataset_integrity.py
- piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_1.md

## Exact behavior
- Random rows and Sequential rows now group source images and synthetic derivatives by their session-scoped source_frame_id or frame_id, plus normalised image paths. Connected identities remain wholly in either Train or Validation.
- Session split keeps sessions intact; if the same image file appears in two sessions, those sessions cannot be separated across partitions.
- Random splitting is still seeded/deterministic. Sequential splitting follows source-family first occurrence rather than the appended position of synthetic rows.
- No synthetic/source family can be split to manufacture validation data. If only one independent family exists, the validation dataset is empty, and training can proceed without validation rather than show a misleading validation result.
- Validation ratios are approximate when source groups have multiple rows; this is intentional to avoid leakage.
- Preprocess datasets save to preprocessed_YYYYMMDD_HHMMSS; any same-second collision uses _02, _03 and so on. Exclusive mkdir prevents concurrent requests from selecting an occupied directory.
- Existing saved datasets and source images are not rewritten; no config or output schema changes.
- Version: 0.11.1 / piTrainer_0_11_1.

## Verification actually performed
In the local environment, starting from the uploaded piTrainer_0_11_0.zip (the source blob hashes of split_service.py and preprocess_service.py match the current GitHub baseline):
- python -m unittest discover -s tests -v: **10 tests passed**.
- python -m compileall -q piTrainer tests main.py: passed.
- Imported split_service and preprocess_service: passed.
Tests exercise the real preprocessing augmentation function, random/sequential/session splits, same-image and same-source grouping, single-family behavior, legacy rows, deterministic results, and same-second CSV/JSONL/recipe preservation.

## Known limits / follow-up
- Real Windows PySide6 UI operation and TensorFlow model training were not exercised in this environment.
- Near-duplicate photographs at different paths without source metadata are not identified by content hashing; this fix prevents known-source leakage, not temporal similarity between adjacent camera frames. Session-level validation is still advisable for realistic generalization measurement.
- Training and validation counts can differ from the exact requested percentage when entire source families must be grouped.
- If writing CSV/JSONL/recipe raises an exception, its uniquely reserved folder may retain incomplete output; recovery/cleanup remains separate future work.
