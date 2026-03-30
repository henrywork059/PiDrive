# PATCH NOTES — CustomTrainer 0_2_6

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_5** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Move the quick-deploy workflow so it lives **only on the Marking tab** instead of the Training tab.

The user wanted the fast "load trained model and try it on frames" flow to stay where the frames already are, rather than mixing it into the Training page.

## Problems addressed
1. Quick Deploy was still presented on the Training tab even after the user clarified that it should belong on **Marking only**.
2. That made the workflow harder to follow because the user had to leave the frame-labeling context to run a quick prediction pass.
3. The Training page had started carrying prediction-specific UI that was no longer the intended home for that feature.

## Likely root cause
- Patch `0_2_4` first added Quick Deploy to Training.
- Patch `0_2_5` then refined that Training-only flow.
- The later clarification narrowed the UX requirement further: the feature should not live on Training at all; it should live on **Marking**, where the current frame and current session already exist.

## Changes made

### 1) Added Quick Deploy To Frames on the Marking tab
- Added a new **Quick Deploy To Frames** panel directly on the **Marking** page.
- Added controls to:
  - browse to a trained `.pt` file
  - browse to a frame file or frame folder
  - auto-fill the latest `best.pt`
  - auto-fill the **current frame**
  - auto-fill the **current session frames**
  - run **Quick Predict Here** without leaving Marking

### 2) Added quick-deploy result preview on Marking
- Added a small saved-result preview area inside the Marking tab.
- Added a result browser with:
  - **Prev Result**
  - **Next Result**
  - a drop-down result selector
- Parsed the same prediction markers already emitted by the internal Ultralytics runner so saved output images can be stepped through directly on Marking.

### 3) Removed Quick Deploy from the visible Training layout
- Removed the Quick Deploy UI from the Training page layout so the user no longer sees that feature there.
- Training now focuses again on training configuration, run logs, and live metric plots.
- Kept the recently accepted training improvements intact while moving the user-facing quick-deploy workflow back to Marking.

### 4) Updated docs and visible version
- Updated the main window title to **CustomTrainer 0_2_6**.
- Updated the shortcut/help dialog text so it points to Marking for quick deploy.
- Updated the Marking help text and README workflow notes to describe the new Marking-only location for quick deploy.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_6.md`

## Exact behavior changed
Before this patch:
- Quick Deploy was exposed on the **Training** tab.
- The user had to leave the Marking context to run a quick frame prediction pass.

After this patch:
- Quick Deploy is exposed on the **Marking** tab only.
- The user can stay in Marking, pick the latest trained weights, choose the current frame or current session frames, run quick prediction, and browse the saved results there.

## Verification actually performed
- Reviewed the recent CustomTrainer patch notes (`0_2_5`, `0_2_4`, `0_2_3`) before patching to avoid rollback of:
  - startup-safe device probing
  - dataset / label preflight fixes
  - Marking shortcuts and per-class colors
  - top-level-only session scanning
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Manually reviewed the moved Quick Deploy flow in the modified files to confirm the user-facing location is now Marking rather than Training.

## Known limits / next steps
- The hidden helper code paths on Training were not fully deleted in this patch; the visible Quick Deploy workflow is what was moved. A later cleanup patch can remove unused internal helper code if desired.
- Quick Deploy on Marking currently uses a fast fixed prediction setup (`imgsz=640`, `conf=0.25`, `device=auto`) for simplicity.
- A later patch could add a small per-run confidence / image-size control on Marking if the user wants more tuning without opening Validation.
