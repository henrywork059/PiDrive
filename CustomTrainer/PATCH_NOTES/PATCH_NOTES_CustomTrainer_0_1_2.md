# PATCH NOTES — CustomTrainer 0_1_2

## Goal

Make CustomTrainer behave much more like piTrainer for day-to-day dataset work:

- load all sessions from a chosen folder
- keep the PySide6 desktop style
- reduce the app to one main marking workflow
- let the user browse sessions and label images in one place

## Why this patch was needed

Version 0_1_1 moved CustomTrainer to PySide6, but it still kept a broad multi-tab trainer/export structure.
That did **not** match the requested workflow.

The user asked for something closer to piTrainer's practical dataset handling:

- open one folder
- see all sessions
- choose a session
- browse its images
- label directly in the app

So this patch changes the app from a broad trainer shell into a **session-based labeling tool**.

## Main changes

### 1) Simplified UI to one marking workflow

Replaced the earlier multi-page workflow with a single main **Marking** tab.

This makes the app behave more like a focused data tool rather than a training launcher.

### 2) Added session-root scanning

Added a new `session_service.py` that:

- scans a chosen root folder
- discovers session folders automatically
- supports multiple common image/label layouts
- tracks session image counts and label paths

### 3) Added piTrainer-like session browsing flow

The main page now includes:

- Session Source panel
- Sessions list panel
- Images list panel
- Image Preview panel
- Classes panel
- Annotation Tools panel
- Current Item info panel
- docked Log Console

This matches piTrainer more closely in workflow and layout feel.

### 4) Rebuilt the labeler around session/image selection

The annotation flow now supports:

- left-drag to create box
- right-click to select box
- Delete key or button to remove selected box
- class assignment for new boxes
- class reassignment for selected boxes
- keyboard nudging for selected boxes
- save labels in YOLO `.txt` format

### 5) Added class file support

CustomTrainer now tries to load class names from:

- `classes.txt`
- `dataset.yaml`
- `data.yaml`

The class editor can also save a new `classes.txt`.

### 6) Reduced dependency weight

Removed unused heavy training/runtime dependencies from `requirements.txt`.
The patch now only requires:

- `PySide6`
- `PyYAML`

## Files added / replaced

- `CustomTrainer/run_custom_trainer.py`
- `CustomTrainer/requirements.txt`
- `CustomTrainer/README.md`
- `CustomTrainer/custom_trainer/__init__.py`
- `CustomTrainer/custom_trainer/app.py`
- `CustomTrainer/custom_trainer/state.py`
- `CustomTrainer/custom_trainer/services/__init__.py`
- `CustomTrainer/custom_trainer/services/session_service.py`
- `CustomTrainer/custom_trainer/services/yolo_io.py`
- `CustomTrainer/custom_trainer/ui/__init__.py`
- `CustomTrainer/custom_trainer/ui/styles.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/custom_trainer/ui/pages/__init__.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/widgets/__init__.py`
- `CustomTrainer/custom_trainer/ui/widgets/annotation_canvas.py`
- `CustomTrainer/custom_trainer/ui/widgets/log_panel.py`

## Verification performed

### Static verification

- checked Python syntax with `python -m compileall`
- verified imports and package paths are internally consistent
- verified the app structure is self-contained in the zip

### Runtime limitation in this environment

A full GUI launch test could not be completed here because `PySide6` is not installed in this container.

## Known limitations

- box resizing handles are not included yet
- labels are focused on YOLO rectangle annotation only
- this patch removes the broader multi-tab training/export flow on purpose, to match the requested marking-first workflow

## Recommended next improvements

- add box resize handles and drag-move with mouse
- add zoom / pan controls in the preview
- add per-session class profiles
- add auto-next-after-save option
- add image filters such as unlabeled-only / labeled-only
