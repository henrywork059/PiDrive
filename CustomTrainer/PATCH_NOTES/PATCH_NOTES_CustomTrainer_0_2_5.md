# PATCH NOTES — CustomTrainer 0_2_5

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_4** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Adjust the new Quick Deploy workflow so it stays **inside the Training tab only** instead of handing off to Validation.

The user wanted the trained model to be applied quickly to the chosen frame / frame folder directly from Training, without changing tabs.

## Problems addressed
1. The previous Quick Deploy flow pushed the selected model and source into the Validation tab.
2. That extra tab switch broke the intended "quick try the trained model on frames" workflow.
3. Training already had a preview area and run log, so the handoff added friction instead of reducing it.

## Likely root cause
- Patch 0_2_4 reused the existing Validation prediction pipeline to minimize duplicated inference logic.
- That worked technically, but it did not match the user's requested UX: the Quick Deploy action should have remained in Training.

## Changes made

### 1) Quick Deploy now runs directly inside Training
- Reworked `TrainPage` so **Quick Deploy To Frames** no longer sends the model/source into Validation.
- Added a direct **Quick Predict Here** action on the Training page.
- Quick prediction now launches from Training using the existing internal Ultralytics CLI runner.

### 2) Training preview can now show quick-deploy results
- Expanded the Training preview area so it can show:
  - the raw selected frame / folder preview before prediction
  - the saved predicted output frames after quick prediction finishes
- Added a small result browser with:
  - **Prev Result**
  - **Next Result**
  - a drop-down frame selector

### 3) Training run log now also covers quick deploy prediction
- Reused the Training page log console for quick prediction output.
- Parsed prediction output markers such as saved preview frames and save-directory messages so the Training tab can show results immediately.

### 4) Kept recent accepted fixes intact
This patch was built forward while preserving the latest accepted CustomTrainer fixes:
- 0_2_1 startup-safe Torch/CUDA device probing
- 0_2_2 dataset cache / usable-label preflight checks
- 0_2_3 Marking shortcuts, auto-save, and per-class colors
- 0_2_4 top-level-only frame scanning

### 5) Version / docs updated
- Updated the visible main window title to **CustomTrainer 0_2_5**.
- Updated the in-app shortcut/help text so it no longer says Training Quick Deploy hands off to Validation.
- Updated the README workflow notes to describe the new Training-only quick deploy behavior.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_5.md`

## Exact behavior changed
Before this patch:
- Training Quick Deploy could pick a model and frame source, but prediction was handed off into Validation.

After this patch:
- Training Quick Deploy stays inside the **Training** tab.
- You can:
  - pick the latest `best.pt` or browse to a `.pt`
  - pick the current session frames, a single frame file, or a frame folder
  - click **Quick Predict Here**
  - review the saved prediction outputs immediately in the Training preview area

## Verification actually performed
- Reviewed the latest CustomTrainer patch notes (`0_2_4`, `0_2_3`, `0_2_2`, `0_2_1`) before patching to avoid rollback.
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Manually reviewed the updated Training-page prediction flow to confirm it no longer depends on the Validation handoff for quick deploy.

## Known limits / next steps
- Validation still remains useful for full validation metrics and the larger dedicated prediction workflow.
- Quick Deploy on Training currently uses the Training page's image-size setting and the default confidence of `0.25` for its fast prediction path.
- A later patch could expose additional quick-deploy controls on Training such as confidence, line width, or label display toggles if needed.
