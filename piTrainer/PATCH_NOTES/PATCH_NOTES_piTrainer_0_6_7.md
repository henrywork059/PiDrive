# PATCH NOTES — piTrainer_0_6_7 Bulk Selected-Frame Steering/Speed Edit Patch

## Request summary
- In `Data Workflow > 3 Review`, add a new panel for editing multiple selected frames.
- Allow users to apply a bulk edit to only steering or only speed, one field at a time.
- Add confirmation and warning so users understand the edit will overwrite selected frame labels.

## Cause / root cause
V6.3 added multi-row Record Preview selection and batch deletion, while V6.6 improved the single-frame steering slider. However, the only steering/speed correction workflow still edited one current frame from the image preview. When several frames needed the same correction, users had to repeat the same edit frame by frame.

The edit service also always wrote both steering and speed together. That was safe for single-frame edits, but a bulk workflow needs true field-specific writes so applying speed only does not rewrite steering, and applying steering only does not rewrite speed.

## Files changed
- `piTrainer/piTrainer/panels/data/bulk_edit_panel.py`
  - New `BulkEditPanel` for `3 Review`.
  - Shows selected-frame count from Record Preview.
  - Provides a centred steering slider/spin box and a normal speed slider/spin box.
  - Provides separate `Apply Steering Only` and `Apply Speed Only` buttons.
  - Requires an overwrite-confirmation checkbox before apply buttons are enabled.
- `piTrainer/piTrainer/pages/data_page.py`
  - Adds `Bulk Edit Selected Frames` to `Data Workflow > 3 Review`.
  - Wires Record Preview selection count into the bulk edit panel.
  - Adds bulk steering and bulk speed callbacks.
  - Shows a final warning confirmation dialog before writing bulk edits.
  - Applies only the chosen field to selected records.
  - Updates loaded DataFrames, statistics, plot, and preview after successful bulk edits.
- `piTrainer/piTrainer/services/data/edit_service.py`
  - Adds optional `update_steering` and `update_throttle` flags to `update_frame_controls()`.
  - Preserves backwards compatibility because both flags default to `True`.
  - Supports true steering-only or speed-only JSONL writes for batch edits.
  - Updates top-level record fields and nested `training_label` fields only for the selected field.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_7_bulk_selected_frame_edit` so saved UI state does not hide the new Review panel arrangement.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.7` / `piTrainer_0_6_7`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents the new batch frame editing behaviour and one-field-at-a-time rule.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve the bulk selected-frame edit panel and safety flow.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_7.md`
  - This patch note.

## Exact behaviour changed
- `Data Workflow > 3 Review` now contains:
  - `Bulk Edit Selected Frames` expanded by default;
  - `Merge Sessions` collapsed by default;
  - `Overlay Controls` collapsed by default.
- Users can select multiple rows in `Data Review > 1 Records`, then use `3 Review > Bulk Edit Selected Frames` to apply:
  - steering only; or
  - speed/throttle only.
- Bulk steering uses the same centred-fill slider logic as the V6.6 Edit Steering slider.
- Bulk speed uses the normal left-to-right slider logic.
- The bulk apply buttons stay disabled until:
  - at least one frame row is selected; and
  - the user ticks `I understand this will overwrite selected frame labels`.
- Even after the checkbox is ticked, each bulk edit still opens a warning confirmation dialog before writing.
- Applying steering only writes steering fields only and preserves speed/throttle fields in `labels.jsonl` / `records.jsonl`.
- Applying speed only writes speed/throttle fields only and preserves steering fields in `labels.jsonl` / `records.jsonl`.
- After successful bulk edits, the in-memory dataset, filtered dataset, stats, plot, and preview are refreshed.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- Frame Filter remains in `2 Manage`.
- Merge Sessions remains in `3 Review` and collapsed by default.
- Data Control remains expanded by default.
- Batch frame deletion and the Data Control delete confirmation checkbox remain unchanged.
- `frame_id` remains the first Record Preview column.
- Record Preview first-column anchoring remains unchanged.
- Playback controls remain directly under the image preview.
- Single-frame Image Preview steering/speed editing remains available.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading is unchanged.
- PiSD V7 overlay redraw and overlay metadata support are unchanged.
- Preprocess, Train, Validate, and Export workflow logic is unchanged.
- V6.6 colour semantics, scrollbar thickness, splitter handle thickness, and centred single-frame steering slider remain unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.6` install.
- `update_frame_controls()` remains backwards-compatible for existing callers because the new field-select flags default to writing both steering and speed.
- The bulk edit panel uses existing selected Record Preview rows; it does not introduce a new dataset selection model.
- The overwrite checkbox is intentionally not persisted. Users must confirm bulk edits again after restarting the app.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1`, `0_6_2`, `0_6_3`, `0_6_4`, `0_6_5`, and `0_6_6` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_6.md`
  - `PATCH_NOTES_piTrainer_0_6_5.md`
  - `PATCH_NOTES_piTrainer_0_6_4.md`
  - `PATCH_NOTES_piTrainer_0_6_3.md`
- Confirmed this patch does not intentionally roll back:
  - PiSD V7 labels/records support;
  - PiSD V7 overlay redraw support;
  - preprocessing/manual-drive fixes;
  - training-start preflight fixes;
  - full-width splitter layout;
  - horizontal overflow scroll behaviour;
  - V6.1 playback-under-preview layout;
  - V6.2 Data Workflow and Data Review tab orders;
  - V6.2 AI-agent instruction document;
  - V6.3 Data Control delete checkbox;
  - V6.3 multi-row selection and batch delete support;
  - V6.3 `frame_id` first-column order;
  - V6.4 first-column anchoring;
  - V6.4 removal of `Next Step:` and `Show:` visible label prefixes;
  - V6.5 central theme token system;
  - V6.5 slim splitter handle values;
  - V6.6 amber/green action colour semantics;
  - V6.6 scrollbar thickness;
  - V6.6 centred single-frame steering slider.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_6_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected the current Data page, Record Preview selection helpers, Image Preview edit flow, edit service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a focused temporary JSONL edit-service check confirming:
  - speed-only updates preserve existing steering in both top-level fields and nested `training_label`;
  - steering-only updates preserve existing speed/throttle in both top-level fields and nested `training_label`.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.7`;
  - `PATCH_VERSION` reports `piTrainer_0_6_7`;
  - `FORMAT_VERSION` reports `0_6_7_bulk_selected_frame_edit`;
  - `BulkEditPanel` exists and uses `CenteredFillSlider` for steering;
  - `Data Workflow > 3 Review` includes `Bulk Edit Selected Frames`;
  - bulk apply paths call `update_frame_controls()` with field-specific update flags.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6 to identify only intended changed/new files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch changes Data page batch label editing and the shared edit service only.

## Known limits / next steps
- The bulk edit panel refreshes the table after applying edits, so multi-selection may collapse back to one selected row after a successful edit. This is safer for immediate visual confirmation, but a later patch could restore the full edited multi-selection if needed.
- There is no automatic undo stack for bulk JSONL edits. The confirmation checkbox and warning dialog are intentionally retained for safety.
