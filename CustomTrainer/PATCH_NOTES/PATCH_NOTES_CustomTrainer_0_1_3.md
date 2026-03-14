# PATCH NOTES — CustomTrainer 0_1_3

## Goal
Restore the extra workflow tabs requested by the user while keeping the stronger 0_1_2 session-based marking workflow.

## Main changes

### 1. Restored multi-tab shell
CustomTrainer now has these top-level pages again:
- Marking
- Training
- Validation
- Export

This keeps the single dedicated **Marking** workflow while bringing back the other work stages the user asked for.

### 2. Kept the 0_1_2 session-driven marking flow
The Marking page still:
- loads a sessions root folder
- scans all sessions inside it
- lists sessions and images
- lets the user label images in one main marking tab
- saves YOLO label files
- edits/saves `classes.txt`

### 3. Added working training / validation / export runners
Instead of depending on the external `yolo` command, this patch adds:
- `custom_trainer/services/ultralytics_runner.py`
- `custom_trainer/services/ultralytics_cli.py`

These launch Ultralytics through Python using:
- training
- validation
- prediction
- export

This is more self-contained and easier to run from the GUI.

### 4. Shared state improvements
The app state now exposes:
- current session
- current image
- preferred dataset yaml path from the active sessions root

This allows the other tabs to pull defaults from the currently loaded dataset folder.

## Files changed / added
- `CustomTrainer/custom_trainer/state.py`
- `CustomTrainer/custom_trainer/ui/main_window.py`
- `CustomTrainer/custom_trainer/ui/qt_helpers.py`
- `CustomTrainer/custom_trainer/ui/pages/__init__.py`
- `CustomTrainer/custom_trainer/ui/pages/marking_page.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/pages/export_page.py`
- `CustomTrainer/custom_trainer/services/ultralytics_runner.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/README.md`
- `CustomTrainer/requirements.txt`

## Verification performed
- syntax-checked all Python files with `py_compile`
- verified zip structure and patch notes

## Notes / limitations
- Full GUI runtime launch could not be tested in this container because `PySide6` is not installed here.
- Training / validation / export require the user environment to have the dependencies installed from `requirements.txt`.
