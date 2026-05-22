# PATCH NOTES — piTrainer_0_5_3 Version Display Patch

## Request summary
- Provide patch-only delivery rather than a full package.
- Show the current piTrainer patch/version number directly in the application window.
- Build forward from the accepted V5.2 unified-format state without changing existing trainer behaviour.

## Cause / root cause
V5.2 centralised the visual format system, but the running application window did not visibly show which package/patch version was installed. This made it harder to confirm whether a PC was running the latest patch after extracting zip updates or pulling from Git.

## Files changed
- `piTrainer/piTrainer/version.py`
  - New central version constants for the visible application/version labels.
- `piTrainer/piTrainer/app.py`
  - Uses the central application name and version through Qt's application metadata.
- `piTrainer/piTrainer/main_window.py`
  - Shows the version in the window title.
  - Adds a permanent status-bar version label so the installed patch can be checked without opening files.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_5_3.md`
  - This patch note.

## Exact behaviour changed
- Window title now includes `piTrainer 0.5.3`.
- Status bar now permanently shows `Version 0.5.3 (piTrainer_0_5_3)`.
- Startup ready message also includes the same version text.
- Qt application metadata now uses `piTrainer` as the application name and `0.5.3` as the application version.

## Preserved behaviour
- All V5.2 unified presentation-format behaviour is preserved.
- All V5.1 responsive splitter/layout behaviour is preserved.
- All V5.0 accepted functionality is preserved.
- PiSD V7 `labels.jsonl` / `records.jsonl` support is preserved.
- PiSD V7 overlay redraw is preserved.
- Preprocessing/manual-drive fixes are preserved.
- Training-start checks are preserved.
- Green, full-width Next Step buttons are preserved.

## Rollback-risk check
- Checked current V5.2 code before patching.
- Checked the latest patch notes `0_5_2`, `0_5_1`, and `0_5_0` before patching.
- This patch only adds visible version metadata and a status-bar label.
- It does not edit trainer data loading, preprocessing, training, validation, export, overlay, splitter, or formatting logic.

## Verification actually performed
- Built forward from `piTrainer_0_5_2_full.zip` working state.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Checked the package diff against V5.2 to confirm only the intended version-display files and patch note are included.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox because PySide6 is not installed here.
- Full TensorFlow training was not run because this patch only changes version display metadata.

## Known limits / next steps
- Future patches should update `piTrainer/piTrainer/version.py` so the app window always reports the installed version accurately.
