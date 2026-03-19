# PATCH NOTES — CustomTrainer 0_1_11

## Scope
Patch-only update for CustomTrainer based on the latest delivered baseline **CustomTrainer_0_1_10**.

## Problems addressed
1. The app did not automatically reload the last sessions root, so the user had to browse for the same folder every launch.
2. Several tabs were still mostly stacked layouts instead of having enough draggable panel boundaries for easier workspace control.
3. Training lacked an in-page visual progress plot while a run was active.
4. Validation prediction was still too limited for visual review across a whole frame set.
5. Validation did not expose enough control over the rendered prediction overlay style.

## Likely causes
- There was no persistent UI-state storage for the last sessions root or splitter sizes.
- Training already had logs, but no live reader for Ultralytics `results.csv`.
- Validation preview was centered around a single current image rather than a saved prediction-frame browser.
- Prediction rendering depended on default Ultralytics save behavior rather than explicit plotting controls.

## Changes made

### 1) Persistent last loaded sessions root
- Added a lightweight local UI-state service at `CustomTrainer/config/ui_state.json`.
- Marking now saves the last successfully scanned sessions root.
- On startup, the main window asks Marking to restore and auto-scan the last valid sessions root.

### 2) More draggable split panels
- Marking now uses additional nested splitters for the left and right panes.
- Training now uses splitters across config / plot+log / preview+notes.
- Validation now uses splitters across config / preview+browser / log+notes.
- Export now uses splitters across config and log+notes.
- Splitter sizes are persisted and restored between launches.

### 3) Live training progress plot
- Added a reusable line-plot widget.
- Training now polls Ultralytics `results.csv` during an active run.
- The page exposes a metric selector so the user can switch which metric is plotted.
- Training plot state updates as new rows are written during the run.

### 4) Validation frame browser for full-frame review
- Validation can now target a whole frames folder more naturally.
- **Use Current Session Frames** points prediction at the current session image directory.
- Prediction saves model-rendered output frames and the UI collects them into a browser.
- Added **Prev Frame / Next Frame** controls and a frame selector drop-down.
- This makes it easier to visually inspect model performance over many frames instead of a single image.

### 5) Prediction overlay controls
- Added validation controls for:
  - box line width
  - label text size
  - show labels
  - show confidence
  - show boxes
- The internal prediction runner now passes these options through to explicit plotted output generation.

### 6) Extra page-local logging
- Validation now has its own run log.
- Export now has its own run log.
- Training keeps its own run log while also driving the live plot.

## Files changed
- `CustomTrainer/README.md`
- `CustomTrainer/custom_trainer/services/ui_state_service.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/services/ultralytics_runner.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/custom_trainer/ui/pages/export_page.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/widgets/line_plot_widget.py`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_1_11.md`

## Verification performed
- Static review against the provided PiDrive repo structure and the GitHub `CustomTrainer/` path.
- `python -m compileall custom_trainer run_custom_trainer.py`

## Notes / limitations
- Full GUI runtime testing was not possible in this container because a desktop PySide6 session is not available here.
- The live training plot depends on Ultralytics writing `results.csv` during training.
- Validation folder prediction assumes the selected source contains image frames when you want a frame-by-frame browser.
