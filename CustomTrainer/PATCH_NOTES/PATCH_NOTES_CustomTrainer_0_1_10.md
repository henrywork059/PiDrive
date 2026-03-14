# PATCH NOTES — CustomTrainer 0_1_10

## Goal
Update the **Mark** tab controls to work more like a fast annotation workflow:
- `W / A / S / D` move the selected box
- `Up / Down` switch frame
- `Ctrl + Click` multi-select frames
- `Delete` removes selected frames

## Main changes

### 1) Box movement moved to W/A/S/D
Updated:
- `custom_trainer/ui/widgets/annotation_canvas.py`

Changes:
- selected box now moves with `W / A / S / D`
- `Shift` still increases the nudge step
- `Backspace` deletes the selected box
- `Up / Down` now request previous / next frame from the Mark page

### 2) Frame list now supports multi-select
Updated:
- `custom_trainer/ui/pages/marking_page.py`

Changes:
- frame list selection mode changed to **ExtendedSelection**
- users can use `Ctrl + Click` to select multiple frames

### 3) Delete selected frames from the Mark page
Updated:
- `custom_trainer/ui/pages/marking_page.py`

Changes:
- added **Delete Selected Frame(s)** action
- `Delete` on the frame list removes selected image files and their label files from disk
- current session list and counts refresh after deletion
- label cache files are invalidated after save/delete so training sees the updated labels/frames

### 4) Help text and version updated
Updated:
- `custom_trainer/ui/main_window.py`
- `README.md`

Changes:
- help dialog reflects the new Mark tab controls
- window title / docs updated to `CustomTrainer 0_1_10`

## Files changed
- `CustomTrainer/custom_trainer/services/session_service.py`
- `CustomTrainer/custom_trainer/ui/widgets/annotation_canvas.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_10.md`

## Notes
Deleting frames is a real filesystem delete, not a hide/remove-from-list action.
The app will ask for confirmation before deleting selected frames.
