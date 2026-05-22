# PATCH NOTES — piTrainer_0_6_3 Data Manage Multi-Delete and Layout Refinement Patch

## Request summary
- Add a confirmation checkbox in Data Control for delete actions so the app does not ask with a popup every time.
- Allow users to select multiple frames in the Record Preview table.
- Make `frame_id` the first Record Preview table column.
- Collapse Merge Sessions by default.
- Move Frame Filter into the Manage workflow.
- Make the amber Browse button colour more yellowish.

## Cause / root cause
The V6.2 Data page had the correct high-level tab order, but the detailed control placement and delete workflow still needed refinement:

- Deleting frames still used a modal confirmation dialog on every delete action.
- The Record Preview table only allowed single-row selection, which made batch cleanup slow.
- `frame_id` was present but not the first column, so the most useful row identifier was not immediately visible.
- Frame Filter was still grouped under Review even though it is a dataset-management tool.
- Merge Sessions was expanded by default, taking space in normal review workflows.
- The amber Browse colour looked too brown and not yellow enough.

## Files changed
- `piTrainer/AGENTS.md`
  - Updates AI-agent guidance for the new V6.3 Data page rules.
  - Records that Frame Filter belongs in `2 Manage`, Merge Sessions belongs in `3 Review` but collapsed, `frame_id` should stay first, and delete should use the Data Control checkbox flow.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents multi-row Record Preview selection.
  - Documents `frame_id` as the first visible Record Preview column.
  - Documents Frame Filter in Manage and Merge Sessions collapsed in Review.
  - Updates delete-confirmation guidance from repeated popups to a Data Control checkbox.
  - Notes that amber should be more yellowish than brown.
- `piTrainer/piTrainer/pages/data_page.py`
  - Moves `Frame Filter` into `Data Workflow > 2 Manage`.
  - Keeps `Data Control` expanded by default.
  - Leaves `Merge Sessions` in `Data Workflow > 3 Review` but collapsed by default.
  - Updates Data Review helper text for multi-select frame cleanup.
  - Changes deletion logic to delete all selected Record Preview rows.
  - Requires the Data Control confirmation checkbox before deleting.
  - Removes the repeated per-delete confirmation dialog once the checkbox is ticked.
  - Reports successful deletes through the status bar instead of a success popup.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Adds `I confirm frame delete actions` checkbox.
  - Updates helper text for selected record rows and the no-repeated-popup behaviour.
  - Renames the destructive button to `Delete Selected Frame(s)`.
  - Adds `deletion_confirmed()` for the Data page delete flow.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Changes the Record Preview table selection mode from single selection to extended multi-row selection.
  - Adds `selected_records()` and `selected_source_rows()` helpers for batch deletion.
  - Keeps the current focused row driving the image preview while allowing multiple rows to remain selected.
  - Improves row identity handling when the table is sorted.
  - Keeps playback movement based on visible table rows.
  - Updates the summary label to show when multiple rows are selected.
- `piTrainer/piTrainer/services/data/preview_service.py`
  - Reorders preview columns so `frame_id` is first.
- `piTrainer/piTrainer/main_window.py`
  - Updates the F1 shortcut description for Delete to describe selected frame rows and the Data Control checkbox.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_3_multi_delete_manage_filter_yellow_browse` so older saved layouts do not hide the new default Data page arrangement.
- `piTrainer/piTrainer/ui/styles.py`
  - Changes the `amber` button role to a brighter, more yellowish amber.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.3` / `piTrainer_0_6_3`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_3.md`
  - This patch note.

## Exact behaviour changed
- Data Workflow remains ordered as:
  - `1 Load`
  - `2 Manage`
  - `3 Review`
- `2 Manage` now contains:
  - `Data Control` expanded by default.
  - `Frame Filter` expanded by default.
- `3 Review` now contains:
  - `Merge Sessions` collapsed by default.
  - `Overlay Controls` collapsed by default.
- Record Preview allows multi-row selection.
- Deleting with the button or keyboard Delete removes all selected frame rows, not only one row.
- Delete actions require the new Data Control checkbox to be ticked first.
- Once the checkbox is ticked, delete actions no longer show a confirmation dialog every time.
- Successful delete completion is shown in the status bar instead of a success popup.
- Failed delete operations still show a warning popup with the failure messages.
- Record Preview columns now place `frame_id` first.
- Browse/location buttons using the shared `amber` role are now more yellowish.
- The app window/status version now reports `0.6.3`.

## Behaviour intentionally not changed
- The Data page still uses the V6 full-width three-panel splitter layout.
- Playback controls remain directly under the image preview from V6.1.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot` from V6.2.
- Merge Sessions remains in the Review workflow as requested in V6.2; only its default expanded state changed.
- The old generic `Data Actions` panel is still not used in the active Data page layout.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Edit/delete services still update `labels.jsonl` and `records.jsonl` where available.
- Preprocess, Train, Validate, and Export workflow logic is unchanged except for shared amber button styling.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6/V6.1/V6.2 install.
- `FORMAT_VERSION` was bumped so the new default Data page arrangement is not hidden by older saved splitter/tab layout state.
- Batch deletion uses the existing single-frame delete service repeatedly, preserving current JSONL/image deletion behaviour.
- The checkbox is intentionally not stored as a persistent setting; users must explicitly confirm destructive cleanup again after restarting the app.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `piTrainer_0_6_1_patch.zip` and `piTrainer_0_6_2_patch.zip` applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_2.md`
  - `PATCH_NOTES_piTrainer_0_6_1.md`
  - `PATCH_NOTES_piTrainer_0_6_0.md`
  - `PATCH_NOTES_piTrainer_0_5_7.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support.
  - PiSD V7 overlay redraw support.
  - Preprocessing/manual-drive fixes.
  - Training-start preflight fixes.
  - Full-width splitter layout.
  - Horizontal overflow scroll behaviour.
  - Compact guided banner.
  - Green Next Step buttons.
  - Central formatting/style system.
  - V6.1 playback-under-preview layout.
  - V6.1 stats-inside-Data-Review layout.
  - V6.2 `1 Load`, `2 Manage`, `3 Review` workflow tab order.
  - V6.2 `1 Records`, `2 Stats`, `3 Plot` review tab order.
  - V6.2 AI-agent instruction document.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` and `piTrainer_0_6_2_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the Data page, Record Preview panel, Data Control panel, preview column service, style/format files, AI-agent instructions, style guide, and latest patch notes.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran static source checks confirming:
  - `frame_id` appears before `session` in `preview_service.py`.
  - Record Preview uses `QAbstractItemView.ExtendedSelection`.
  - `PreviewPanel.selected_records()` exists.
  - `DataControlPanel.deletion_confirmed()` exists.
  - Frame Filter is in the Manage workflow.
  - Merge Sessions is in Review and collapsed by default.
  - Amber styling uses the new yellowish colour value.
  - Version metadata reports `0.6.3`.
- Compared the working tree against fresh V6+0.6.1+0.6.2 to identify only intended changed files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch changes Data page cleanup workflow, table selection, documentation, and shared button styling only.

## Known limits / next steps
- Batch deletion currently calls the existing single-frame delete service once per selected row. This is safer and preserves existing behaviour, but a future patch could add a dedicated batch delete service for very large selections.
- If the user wants a visual selected-row count near the delete button, Data Control can be wired to the Record Preview selection state in a later patch.
