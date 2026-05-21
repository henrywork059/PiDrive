# PATCH NOTES — piTrainer_0_4_6

## Request summary
- Fix the issue where piTrainer could not start training after the recent PiSD V7 data/overlay and UI/layout patches.
- Build forward from the latest accepted `piTrainer_0_4_5` state without rolling back V7 overlay support or the readable/collapsible UI layout work.

## Cause / root cause
1. **PiSD V7 `manual_drive` rows could be filtered out during preprocessing.**
   - PiSD V7 records commonly use `manual_drive` as the mode for user-driven training rows.
   - The normal Data-page loader already recognised `manual_drive`, but the Preprocess-page manual-mode filter still only recognised older mode names: `manual`, `user`, and `train`.
   - If the user confirmed preprocessing with `Manual only`, the active dataset could become empty even though valid PiSD V7 rows existed. Training then appeared unable to start because there were no active rows left.

2. **Training start used stale/unchecked split data.**
   - After loading new sessions or confirming preprocessing, `train_df` and `val_df` are intentionally cleared until a new split is prepared.
   - The Start Training action only prepared a split when both cached split dataframes were empty. This made the action less robust if stale split data existed after data changes.
   - The start action also did not clearly report why training could not proceed when image paths were missing/unreadable or steering/speed labels were invalid.

## Files changed
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_4_6.md`

## Exact behaviour changed
- Added `manual_drive` to the Preprocess-page manual-mode set.
- Start Training now always refreshes the training split from the current active dataset before launching the worker.
- Start Training now checks that the active dataset contains the required training columns:
  - `abs_image`
  - `steering`
  - `throttle`
- Start Training now filters split rows to usable rows before launching TensorFlow:
  - image path exists;
  - steering is numeric;
  - speed/throttle is numeric.
- If the configured split leaves no usable training rows but the active dataset contains usable rows, piTrainer now falls back to training from all active usable rows instead of refusing to launch.
- If training still cannot start, the Training Log and status bar now explain the reason clearly instead of only appearing inactive.
- The Training Log now says exactly how many train and validation rows are sent to the worker.

## Compatibility notes
- PiSD V7 `labels.jsonl` / `records.jsonl` loading behaviour from `0_4_0` and `0_4_5` is preserved.
- PiSD V7 overlay metadata and overlay redraw behaviour are preserved.
- The `0_4_1`–`0_4_3` scrollable/collapsible/readable layout redesign is preserved.
- No model architecture, loss function, validation metric, or export artefact logic was changed.

## Rollback-risk check
- Checked the latest patch note `0_4_5` and previous three V4 notes: `0_4_4`, `0_4_3`, and `0_4_2`.
- Preserved the `0_4_5` sorted Record Preview selection and PiSD V7 edit/delete JSONL fixes.
- Preserved the `0_4_4` Export Options startup typo fix.
- Preserved the `0_4_3` whole-program readability redesign and guided workflow tabs.
- Preserved the `0_4_2` tabbed/collapsible panel structure.
- No older file copy was restored over the current accepted state.

## Verification actually performed
- Reconstructed the latest piTrainer state by applying patches forward through `piTrainer_0_4_5` in a clean working folder.
- Ran `python3 -m compileall -q main.py piTrainer` successfully.
- Parsed all Python files with `ast.parse` successfully.
- Ran a service-level test confirming that preprocessing with `mode='manual_drive'` and `Manual only` keeps the row instead of filtering it out.
- Checked the final patch file list to confirm the patch contains only changed files plus this patch note under the correct `piTrainer/...` structure.

## Verification not performed
- A real PySide6 GUI training run was not possible inside this sandbox because PySide6 and TensorFlow are not installed here.
- Full TensorFlow model training should be checked on the Windows PC after applying the patch.

## Known limits / next steps
- If TensorFlow still fails after this patch, the Training Log should now show a clearer reason. Copy the full Training Log or traceback for the next forward hotfix.
- Very small datasets may still train without a validation split; this is intentional so a tiny PiSD test recording can still start training.
