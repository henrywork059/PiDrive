# PATCH NOTES — piTrainer_0_10_1 Validation Frame Review Table and Edit Return Workflow

## Request summary

Optimize the Validation tab Frame Review so that:

- the frame-review table works like the Data page Records table;
- clicking **Edit in Data** opens the same source frame in the Data page for editing;
- returning to the Validation tab restores the same selected validation row;
- rows edited in Data are highlighted in validation review;
- mirrored/generated rows belonging to the edited source frame are highlighted too.

## Cause / root cause

The Data page Records table already used a model-backed `QTableView` with stable source-row mapping, header sorting, first-column anchoring, and keyboard up/down cycling. The Validation Frame Review still used an item-based `QTableWidget` and rebuilt itself from scratch after filter/sort/refresh actions.

That made the validation table easier to lose selection state from, especially after using **Edit in Data**, loading/focusing the source session, and then returning to the Validation tab.

There was also no shared notification path from Data edits back into validation review panels, so validation rows could not show which labels had been changed after the validation run.

## Files changed

- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
  - Replaces the item-based `QTableWidget` review table with the same model/table pattern used by the Data page.
  - Uses `RecordPreviewModel` plus `CyclingPreviewTable` for stable row identity, header sorting, extended row selection, first-column anchoring, and cyclic Up/Down navigation.
  - Keeps the selected validation row identity when **Edit in Data** is clicked.
  - Restores the pending/last validation row when the user returns to the Validation or TFLite Check tab.
  - Tracks edited row groups by session/frame/image identity.
  - Marks edited source rows and mirrored/generated copies after Data edits.
  - Adds edit-marker text to the preview metadata area.
- `piTrainer/piTrainer/panels/data/preview_model.py`
  - Extends the shared table model with validation-column headers and numeric formatting for validation fields.
  - Adds optional row-background highlighting for validation edit markers.
  - Adds tooltip text for rows edited after the validation run.
- `piTrainer/piTrainer/main_window.py`
  - Restores pending frame-review selection when switching back to a page with a frame-review panel.
  - Adds a Data-edit notification bridge to update Validation and TFLite Check frame-review panels.
- `piTrainer/piTrainer/pages/data_page_filter_edit.py`
  - Notifies the main window after successful single-frame image-preview edits.
  - Notifies the main window after successful bulk steering/speed edits.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.10.1 / piTrainer_0_10_1`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_10_1.md`
  - Adds this patch note.

## Exact behavior changed

- Validation Frame Review now behaves like the Data page table:
  - model-backed table;
  - sortable headers;
  - stable source-row mapping after sorting;
  - extended row selection;
  - first column kept visible;
  - Up/Down keyboard cycling through rows.
- The table now starts with frame identity columns closer to the Data page style, with `Frame` first.
- **Edit in Data** stores the exact validation row identity before opening Data.
- When the user switches back to **4 Validate**, the same validation row is reselected when it still exists in the current filter.
- Because the same frame-review panel is reused, the same behavior also applies to **6 TFLite Check**.
- Data edits now mark matching validation rows as edited after the validation run.
- Mirrored/generated validation rows are marked when their source frame was edited.
- Highlighted rows include tooltips and metadata text reminding the user to rerun validation if they want refreshed true/error values.

## Behavior intentionally preserved

This patch does not change:

- model training;
- validation prediction calculations;
- TFLite output parsing;
- normal validation summary metrics;
- Data page label editing logic;
- Data page filtering, hiding/recovering, playback, overlay display, or bulk edit behavior;
- synthetic/mirrored row label correction rules;
- the real entry point `piTrainer/main.py`;
- V10 baseline files outside the targeted table/edit workflow.

## Compatibility / migration notes

- Existing validation results still work; the table is rebuilt from the same result dictionary.
- Existing Data page sessions and metadata files are not migrated or rewritten by this patch.
- Edited-row highlights are session UI markers only. They show that a label was edited after the validation result was produced; they do not silently change the stored validation result metrics.
- Rerun Validation or TFLite Check after editing labels to update the actual target values, errors, plot, and summary metrics.

## Rollback-risk check

Checked the current V10 code state and the latest available notes before finalizing:

- `PATCH_NOTES_piTrainer_0_10_0.md`
- `PATCH_NOTES_piTrainer_0_9_21.md`
- `PATCH_NOTES_piTrainer_0_9_18.md`
- `PATCH_NOTES_piTrainer_0_9_17.md`

Confirmed this patch builds forward from `0.10.0`. It does not restore older Data page table behavior, does not remove the V9 overlay/text changes, and does not change the V10 stable baseline packaging guidance.

## Verification actually performed

- Inspected the current V10 package structure.
- Confirmed the real entry point remains `piTrainer/main.py`.
- Inspected the existing Data page Records table implementation before reusing its model/table pattern.
- Inspected the existing Validation and TFLite Check pages, both of which use `ValidationFrameReviewPanel`.
- Inspected the Data edit path used by image-preview edits and bulk edits.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the updated version file reports `0.10.1 / piTrainer_0_10_1` by static inspection.
- Removed `__pycache__` folders before packaging.
- Prepared a patch-only zip containing only changed files and this patch note.
- Prepared a full `piTrainer_0_10_1.zip` package for convenience.

## Verification not performed

- Live Windows PySide6 GUI startup/clicking was not run in this Linux sandbox because PySide6 is not installed here.
- Real training, validation, and TFLite checks were not run.
- Real row highlighting was not visually inspected in the GUI.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- Highlighted validation rows mean “edited after this validation run”; rerun validation to refresh the numbers.
- Mirrored-row matching uses the available session/frame/source-frame/image identifiers. Very old metadata with missing source identifiers may still rely on the shared image name fallback.
