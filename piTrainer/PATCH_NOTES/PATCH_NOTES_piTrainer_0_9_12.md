# PATCH NOTES — piTrainer_0_9_12 Preview and Overlay Refactor

## Request summary

Continue reviewing the app code so it is split into smaller, easier-to-manage scripts.

## Cause / root cause

After the `0.9.11` Data page split, the next largest and most mixed scripts were still concentrated around Data preview and overlay drawing:

- `piTrainer/panels/data/preview_panel.py` mixed the Records table model, keyboard-aware table subclass, and the full preview panel controller in one file.
- `piTrainer/services/data/overlay_service.py` mixed low-level value helpers, drive-arrow geometry, legacy controls, PiSD road-guide geometry, overlay drawing, and public overlay entry points in one large file.

These files were not broken, but their size made future UI and overlay patches harder to review safely.

## Files changed

- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Keeps the public `PreviewPanel` class and panel behavior.
  - Now focuses on panel layout, selection handling, playback state, and table wiring.
- `piTrainer/piTrainer/panels/data/preview_model.py`
  - New module containing `RecordPreviewModel` and table header/sort/display logic.
- `piTrainer/piTrainer/panels/data/preview_table.py`
  - New module containing `CyclingPreviewTable` and Up/Down row-cycling key handling.
- `piTrainer/piTrainer/services/data/overlay_service.py`
  - Reduced to the public overlay facade used by image preview, validation, and training review panels.
  - Keeps the existing public imports working for `apply_overlays`, `apply_prediction_comparison_overlay`, `clip_speed`, `clip_steering`, `drive_arrow_points`, and `drive_values_from_point`.
- `piTrainer/piTrainer/services/data/overlay_values.py`
  - New module for shared overlay defaults, value parsing, clipping, and drive-arrow coordinate conversion.
- `piTrainer/piTrainer/services/data/overlay_primitives.py`
  - New module for small overlay drawing primitives such as speed bar, steering bar, steering arc, legacy path, and drive arrow.
- `piTrainer/piTrainer/services/data/overlay_road.py`
  - New module for PiSD road-guide geometry and road-guide drawing.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.12 / piTrainer_0_9_12`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_12.md`
  - Adds this patch note.

## Exact behavior changed

No user-facing workflow behavior was intentionally changed.

The structural changes are:

- Records preview code is split into model, table, and panel modules.
- Overlay code is split into values, drawing primitives, PiSD road geometry, and public facade modules.
- `preview_panel.py` is reduced from about 647 lines to about 473 lines.
- `overlay_service.py` is reduced from about 670 lines to about 116 lines.
- New overlay helper modules are smaller and responsibility-focused:
  - `overlay_values.py` about 115 lines.
  - `overlay_primitives.py` about 284 lines.
  - `overlay_road.py` about 211 lines.

## Behavior intentionally preserved

This patch is a maintainability refactor only. It preserves:

- Records table sorting, selection, alternating row display, and current-row behavior.
- Up/Down next-frame navigation after editing, deploying, sorting, and applying AI output.
- Playback FPS maximum of `250`.
- Data Workflow order: `1 Load`, `2 Hide & Recover`, `3 Filter`, `4 Review`, `5 Deploy`.
- Model deploy output columns, diff sorting, overlay preview, and Apply AI to Selected.
- Preprocess completion indicator and default source/mode from `0.9.9`.
- Hide/Recover workflow and hidden permanent-delete shortcut.
- Overlay rendering entry points used by Data preview, Train review, and Validation review.

## Rollback-risk check

Checked the latest current code state and the previous v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_11.md`
- `PATCH_NOTES_piTrainer_0_9_10.md`
- `PATCH_NOTES_piTrainer_0_9_9.md`

Confirmed this patch builds forward from `0.9.11`. It does not replace the Data page with an older copy, does not remove deploy files, and does not roll back the Preprocess, Deploy, table focus, or Hide/Recover fixes.

## Verification actually performed

- Applied all v9 patches from `0.9.0` through `0.9.11` before refactoring.
- Compared the old and new `PreviewPanel` method list and confirmed all 39 existing `PreviewPanel` methods are still present.
- Confirmed the public overlay facade still exposes the same public names through `overlay_service.py`.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the version file reports `0.9.12 / piTrainer_0_9_12`.
- Prepared a patch-only zip with only changed/new files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI startup was not run in this Linux sandbox because PySide6 is not installed here.
- Real image overlay rendering was not visually checked in this sandbox.
- Real TensorFlow/TFLite deployment was not run for this structure-only patch.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- This patch deliberately avoids changing runtime behavior while splitting two large files.
- Other large files still exist, especially validation, preprocessing, editing/delete services, and styles. They can be split in later targeted patches if needed.
