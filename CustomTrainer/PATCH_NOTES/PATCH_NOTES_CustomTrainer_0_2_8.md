# PATCH NOTES — CustomTrainer 0_2_8

## Scope
Patch-only update for CustomTrainer built forward from the delivered patch state **CustomTrainer_0_2_7** and the user-confirmed stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
On the **Marking** tab, remove the visible Quick Deploy panel and replace it with a simple button that quickly deploys the latest trained model onto the **current frame** and loads the predicted boxes into the main Marking canvas.

## Problems addressed
1. The full Quick Deploy panel on Marking added UI clutter the user did not want.
2. The user only wanted the fast current-frame prediction action, not the side controls or side-only result browsing.
3. Replacing the current canvas with zero-box predictions could also wipe the working view unnecessarily.

## Likely root cause
- Patch `0_2_6` moved Quick Deploy onto Marking as a full panel.
- Patch `0_2_7` improved the main-canvas handoff, but the feature still looked like a side workflow instead of a single direct action on the active frame.

## Changes made

### 1) Replaced the visible Quick Deploy panel with a single Marking button
- Removed the **Quick Deploy To Frames** panel from the visible Marking layout.
- Added a single **Quick Deploy Current Frame** button to the Marking tools area.
- The button now uses:
  - the latest available `best.pt`
  - the current active frame on Marking

### 2) Kept the current-frame deploy workflow in the main canvas
- The quick deploy action still routes predictions back into the main Marking canvas as editable boxes.
- The side preview/result browser is no longer part of the visible Marking UI.
- The user can now stay focused on the main frame and refine/save predicted boxes directly there.

### 3) Safer current-frame behavior
- If the current frame has unsaved manual changes, labels are saved before quick deploy runs.
- If quick deploy returns **zero boxes**, existing annotations are left unchanged instead of clearing the current canvas.

### 4) Updated help text / version
- Updated the Marking help text to describe the single-button quick deploy flow.
- Updated the shortcuts/help dialog text.
- Updated the visible main window title to **CustomTrainer 0_2_8**.
- Updated the README workflow notes.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_8.md`

## Exact behavior changed
Before this patch:
- Marking showed a full Quick Deploy side panel with weights/source controls and result browsing.

After this patch:
- Marking shows a single **Quick Deploy Current Frame** button in the tools area.
- Clicking it uses the latest trained `best.pt` on the active frame and loads predicted boxes into the main annotation canvas for editing.
- Zero-box quick deploy results do not wipe existing annotations.

## Verification actually performed
- Reviewed recent CustomTrainer patch notes (`0_2_7`, `0_2_6`, `0_2_5`, `0_2_4`) before patching to avoid rollback of:
  - startup-safe device probing
  - dataset / label preflight fixes
  - Marking shortcuts and per-class colors
  - top-level-only session scanning
  - Marking-canvas quick deploy
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Manually reviewed the Marking-page quick deploy path to confirm the visible side panel is gone and the new button targets the current frame.

## Known limits / next steps
- The internal helper fields for weights/source are still kept in code for the quick-deploy worker path, but they are no longer shown in the Marking UI.
- Quick deploy still depends on finding the latest `best.pt`. If multiple trained runs exist, it will use the latest one discovered by the current state helper.
- A later patch could add an optional second button such as **Quick Deploy Session** if the user wants that workflow back without restoring the full side panel.
