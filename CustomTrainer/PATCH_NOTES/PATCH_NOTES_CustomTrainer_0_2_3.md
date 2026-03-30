# PATCH NOTES — CustomTrainer 0_2_3

## Scope
Patch-only update for CustomTrainer built forward from the user-accepted patch state **CustomTrainer_0_2_2** and the stable baseline **CustomTrainer_0_2_0.zip**.

## Request summary
Improve the Marking-page shortcut workflow for faster labeling while keeping the existing mouse behavior:
- keep left-click drag and right-click select
- `D` = next frame
- `A` = previous frame
- auto-save labels when moving to another frame
- `Delete` = delete selected label/box
- `S` = cycle down to the next label class
- `W` = cycle up to the previous label class
- give each class its own box color

## Problems addressed
1. Frame-to-frame labeling still relied too much on buttons or focus-sensitive canvas keys.
2. Switching frames could interrupt the marking flow with an unsaved-label prompt.
3. Class switching for a selected box required extra clicks on the combo box and apply button.
4. All annotation boxes used the same color, which made different classes harder to distinguish quickly.

## Likely root cause
- The Marking page already had partial keyboard support inside the canvas widget, but the shortcut behavior was not surfaced as a page-level labeling workflow.
- Frame switches still used a generic "save before switching?" prompt instead of the faster auto-save flow requested by the user.
- Annotation rendering used one shared box pen, so class identity was only visible through the numeric label.

## Changes made

### 1) Added page-level labeling shortcuts on the Marking tab
- Added `A` / `D` shortcuts directly on the Marking page for previous / next frame.
- Added `W` / `S` shortcuts to cycle classes.
- Added `Delete` as a direct shortcut for deleting the selected box.
- Kept the existing left-drag create-box and right-click select-box mouse behavior unchanged.

### 2) Auto-save current labels before frame switching
- Reworked the Marking-page frame-switch guard so dirty labels are now saved automatically before switching to another frame.
- If the save fails, the frame switch is blocked and a warning is shown instead of silently losing edits.
- This applies to frame changes triggered by the image list, A/D shortcuts, or Prev/Next buttons.

### 3) Improved class cycling behavior
- `W` / `S` now work in two useful modes:
  - if a box is selected, they cycle that box to the previous / next class immediately
  - if no box is selected, they cycle the active class used for newly drawn boxes
- The status text and selection summary now reflect the updated class more clearly.
- Shortcut handling intentionally ignores text-entry widgets such as the sessions-root field and class editor so normal typing still works there.

### 4) Added per-class annotation colors
- Reworked `AnnotationCanvas` box drawing so each class uses its own persistent color from a deterministic palette.
- Selected boxes now keep a stronger highlight while still showing their class color.
- The class-id label chip is drawn using the same per-class color so class identity is easier to read at a glance.

### 5) Updated visible version / help text
- Updated the main window title to **CustomTrainer 0_2_3**.
- Updated the main shortcut dialog and README to match the new Marking workflow.
- Updated the Marking-page help text so the in-app instructions match the actual shortcut behavior.

## Files changed
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/widgets/annotation_canvas.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_3.md`

## Verification performed
- Reviewed the current Marking-page implementation and recent patch notes to ensure the new shortcut patch did not roll back:
  - the 0_2_1 startup-safe Torch/CUDA probe fix
  - the 0_2_2 dataset-cache / preflight checks
- Ran `python -m compileall custom_trainer run_custom_trainer.py` on the patched CustomTrainer tree.
- Manually checked the updated shortcut wiring, autosave flow, and color-drawing logic in the modified files.

## Known limits / next steps
- `W` / `S` shortcuts are intentionally disabled while typing inside text-entry widgets so users can still edit the sessions path and class list normally.
- The per-class color palette is deterministic and repeated for higher class counts; a later patch could expose user-editable class colors in the UI.
- A later patch could also add direct number-key class selection (`1`..`9`) if faster class jumps are needed.
