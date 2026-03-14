# CustomTrainer 0_1_11 Patch Notes

## Summary
This patch updates the Marking tab controls to match the requested workflow more closely, adds preview panels to Training and Validation, adds stop buttons for long-running tasks, and mirrors a few more convenience features from a trainer-style workflow.

## Main changes

### 1) Marking tab control remap
- Arrow keys now move the selected box.
- `Shift + Arrow keys` moves the selected box faster.
- `A` moves to the previous frame.
- `D` moves to the next frame.
- `X` deletes the selected frame(s).
- `Backspace` and `Delete` delete the selected box.
- `Ctrl + Click` multi-selection for frames remains enabled.

### 2) Training preview + stop button
- Added a **Training Preview** panel that mirrors the current image from the Marking workflow.
- Added a **Refresh Preview** button.
- Added a **Stop Training** button that terminates the running Ultralytics process from the GUI.

### 3) Validation frame preview + stop button
- Added a **Validation Frame Preview** panel for the current image source.
- Added **Refresh Preview**.
- Added **Stop Task** for validation / prediction.

### 4) More useful trainer-side utilities
- Added **Use Latest best.pt** in Validation.
- Added **Use Latest best.pt** in Export.
- Added **Stop Export** in Export.
- Added shared app-state helper to locate the newest trained `best.pt` automatically.

### 5) Command worker improvements
- Added user-stop support to the subprocess runner.
- Runner now logs stop requests and forces termination if a process does not exit quickly.

## Files changed
- `CustomTrainer/custom_trainer/ui/widgets/annotation_canvas.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/pages/export_page.py`
- `CustomTrainer/custom_trainer/ui/qt_helpers.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/custom_trainer/state.py`
- `CustomTrainer/README.md`

## Notes
- This is a patch-only zip. Extract it over the current `CustomTrainer` project.
- Python syntax was checked successfully before packaging.
- Full GUI runtime testing was not possible in this environment because PySide6 is not installed here.
