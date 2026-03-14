# PATCH NOTES — CustomTrainer 0_1_1

## Goal
Convert CustomTrainer from a tkinter-based UI into a PySide6 desktop app and align the overall UI style and app shell with piTrainer.

## Root cause / design gap
The previous CustomTrainer build used tkinter/ttk, while piTrainer uses a PySide6 desktop shell with a darker, more structured panel-based workflow. That meant the two tools felt inconsistent even though they belong to the same repo and broader workflow.

## What changed

### 1) UI framework migration
- Replaced the main CustomTrainer UI layer with **PySide6**.
- Rebuilt the main window as a `QMainWindow` with:
  - tabbed central workflow pages
  - status bar
  - docked bottom log console
  - keyboard shortcuts for page switching

### 2) piTrainer-style visual system
- Added a shared Qt stylesheet using the same dark / blue-accent visual language as piTrainer.
- Applied styled tabs, group panels, inputs, buttons, dock titles, and status areas.

### 3) Page rewrites in PySide6
Rebuilt these UI pages in PySide6 while keeping their existing workflow intent:
- `dataset_page.py`
- `annotate_page.py`
- `train_page.py`
- `validate_page.py`
- `export_page.py`
- `pi_deploy_page.py`

### 4) Logging and worker execution
- Added a Qt log panel widget.
- Added a Qt command worker wrapper so long-running Ultralytics actions can stream logs into the UI without freezing the app.

### 5) Annotation editor carry-over
- Reimplemented the annotation canvas in PySide6.
- Supports:
  - loading image folders
  - reading YOLO labels
  - drawing boxes by drag
  - selecting boxes with right-click
  - deleting selected boxes
  - saving labels back to YOLO format

### 6) Compatibility
- Kept the existing service-layer approach for dataset scanning, Ultralytics command generation, and Pi bundle generation.
- Added `PySide6` to `requirements.txt`.

## Files included in this patch
- `custom_trainer/app.py`
- `custom_trainer/state.py`
- `custom_trainer/services/dataset_service.py`
- `custom_trainer/ui/main_window.py`
- `custom_trainer/ui/styles.py`
- `custom_trainer/ui/qt_helpers.py`
- `custom_trainer/ui/widgets/log_panel.py`
- `custom_trainer/ui/widgets/annotation_canvas.py`
- `custom_trainer/ui/pages/dataset_page.py`
- `custom_trainer/ui/pages/annotate_page.py`
- `custom_trainer/ui/pages/train_page.py`
- `custom_trainer/ui/pages/validate_page.py`
- `custom_trainer/ui/pages/export_page.py`
- `custom_trainer/ui/pages/pi_deploy_page.py`
- `README.md`
- `requirements.txt`
- `PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_1.md`
- `run_custom_trainer.py`

## Verification steps performed
- Rebuilt the UI files as valid Python modules.
- Checked import paths and page wiring.
- Preserved service-module interfaces used by the pages.
- Prepared the patch in patch-only zip structure.

## Remaining future improvements
- Add a richer image list / annotation thumbnail browser.
- Add more piTrainer-like detachable/dockable subpanels inside each page.
- Add training presets and richer validation visualizations.
- Add export-to-PiServer handoff once that flow is finalized.
