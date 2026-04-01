# PATCH NOTES — CustomTrainer 0_2_10

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_9** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Improve the Marking-tab quick deploy flow so the user can:
1. choose the quick deploy model manually
2. run quick deploy on **all selected frames** instead of only the current frame

The user wanted to keep the lightweight Marking-tab workflow rather than bringing back the old side panel.

## Problems addressed
1. Quick Deploy on Marking only auto-used the latest `best.pt`, so the user could not pick a different trained model.
2. Quick Deploy only targeted the current frame, which made it too slow for labeling multiple selected frames in one pass.
3. The current quick-deploy path mainly loaded boxes into the active canvas, but it did not write predictions back to multiple selected label files in one action.

## Likely root cause
- Patch `0_2_8` intentionally simplified the Marking UI to a single quick-deploy button aimed at the current frame.
- That reduced clutter, but it also removed the practical ability to choose a model and batch-apply predictions to a selected subset of frames.

## Changes made

### 1) Added lightweight quick-deploy model selection on Marking
- Added **Choose Quick Deploy Model** to the Marking tools area.
- Added **Use Latest best.pt** beside it for a fast fallback to the newest training output.
- Kept the UI lightweight and did not restore the old side-panel workflow.

### 2) Quick Deploy now targets selected frames
- Changed the main Marking action to **Quick Deploy Selected / Current**.
- If one or more frames are selected in the frame list, quick deploy now runs on those selected frames.
- If no extra frame is selected, it falls back to the current frame.
- For multi-frame selection, the patch stages the selected images into a temporary quick-predict source directory so the existing prediction runner can process just that subset.

### 3) Quick Deploy now writes predicted labels back to disk
- After prediction finishes successfully, the patch converts the predicted pixel boxes back into YOLO labels and writes them to the canonical label paths for the targeted frames.
- Existing labels are kept unchanged when a frame returns no predicted boxes, which avoids wiping manual work on low-confidence or empty predictions.
- The current frame is still focused back into the main Marking canvas when available so the user can inspect or refine it immediately.

### 4) Updated label markers / summary / wording
- Updated the image-list markers so frames that received predicted labels are refreshed immediately.
- Updated the session summary to reflect the current labeled-count after quick deploy writes.
- Updated Marking help text, shortcuts/help wording, README notes, and the visible window title to **CustomTrainer 0_2_10**.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_10.md`

## Exact behavior changed
Before this patch:
- Marking Quick Deploy only auto-used the latest `best.pt`.
- Marking Quick Deploy only targeted the current frame.
- Multi-frame quick labeling still required manual frame-by-frame work.

After this patch:
- the user can choose a `.pt` model explicitly for Quick Deploy
- Quick Deploy can run on all selected frames in the frame list
- predicted labels are written back to those targeted frames automatically when boxes are found
- the current frame can still be loaded into the main Marking canvas for review

## Verification actually performed
- Reviewed recent CustomTrainer patch notes (`0_2_9`, `0_2_8`, `0_2_7`, `0_2_6`) before patching to avoid rollback of:
  - startup-safe device probing
  - dataset / label preflight fixes
  - Marking shortcuts and per-class colors
  - top-level-only session scanning
  - Marking quick-deploy canvas integration
  - Export Validate tab wiring
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Reviewed the new selected-frame quick-deploy flow and label-writeback path in the modified Marking page.

## Known limits / next steps
- Selected-frame quick deploy currently assumes the selected images come from the active session image list, which matches the current Marking workflow.
- If multiple frames in one selected batch share the same filename, source-name matching may still be ambiguous.
- A later patch could add an optional toggle such as **overwrite empty predictions** if the user ever wants zero-box results to explicitly clear existing labels instead of preserving them.
