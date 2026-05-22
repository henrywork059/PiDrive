# PATCH NOTES — piTrainer_0_6_9 Fast Bulk Edit JSONL Batch Patch

## Request summary
- Bulk editing multiple selected frames is taking too much time.
- Optimise the bulk steering/speed edit code so selected frame labels can be updated faster.

## Cause / root cause
The V6.7 bulk edit workflow applied the existing single-frame edit helper once per selected frame. Each selected frame could trigger a separate scan and rewrite of `labels.jsonl` and `records.jsonl`. On large PiSD sessions, that means the same metadata files are repeatedly read and rewritten, so editing many selected frames becomes slow.

The loaded DataFrame update was also done one selected frame at a time. That is acceptable for a few rows, but it becomes unnecessarily expensive when many selected rows are edited together.

## Files changed
- `piTrainer/piTrainer/services/data/edit_service.py`
  - Adds `update_frame_controls_batch()` for fast bulk edits.
  - Groups selected rows by session.
  - Scans each affected `labels.jsonl` / `records.jsonl` file once per bulk edit action.
  - Uses indexed target matching by frame id, image name, and timestamp instead of checking every selected target against every metadata row.
  - Keeps the existing `update_frame_controls()` single-frame API for Image Preview edits.
- `piTrainer/piTrainer/pages/data_page.py`
  - Changes Bulk Edit Selected Frames to call the new batch edit service instead of looping through `update_frame_controls()` once per selected frame.
  - Adds a vectorised loaded-DataFrame update helper so changed steering/speed values are applied to the active dataframes in one pass.
  - Keeps the existing warning checkbox and final confirmation dialog.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_9_fast_bulk_edit_jsonl_batches`.
- `piTrainer/piTrainer/version.py`
  - Updates visible app version to `0.6.9` / `piTrainer_0_6_9`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents that bulk edits must use the batch JSONL updater instead of calling the single-frame updater repeatedly.
- `piTrainer/AGENTS.md`
  - Updates future-agent instructions to preserve the fast batch-edit path.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_9.md`
  - This patch note.

## Exact behaviour changed
- Bulk steering edits now update all selected rows by scanning each affected session metadata file once.
- Bulk speed edits now update all selected rows by scanning each affected session metadata file once.
- The active `dataset_df`, `filtered_df`, and current preview source are updated in one pass after a successful bulk edit.
- Status text now reports how many selected frames were updated and how many metadata rows changed.
- The single-frame edit path in the Image Preview panel remains unchanged.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- Bulk Edit Selected Frames remains in `3 Review`.
- Bulk edits still apply only one field at a time:
  - `Apply Steering Only` changes steering only;
  - `Apply Speed Only` changes speed/throttle only.
- The bulk overwrite checkbox is still required before apply buttons are enabled.
- The final warning confirmation dialog still appears before JSONL files are written.
- Single-frame image preview steering/speed edits still use the existing single-frame update function.
- Soft-delete / hidden-frame handling from V6.8 is unchanged.
- Hidden frames remain excluded from active dataframes, preprocessing, training, and validation.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading and overlay redraw support are unchanged.
- V6.6 amber/green action colour semantics and centred steering sliders are unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.8` install.
- Existing PiSD sessions do not need migration.
- The single-frame `update_frame_controls()` function is kept for compatibility and for Image Preview edits.
- The new batch function writes the same steering/throttle fields as the old single-frame helper, including nested `training_label` values when present.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_8` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_8.md`
  - `PATCH_NOTES_piTrainer_0_6_7.md`
  - `PATCH_NOTES_piTrainer_0_6_6.md`
  - `PATCH_NOTES_piTrainer_0_6_5.md`
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
  - V6.3 Data Control checkbox and multi-row Record Preview selection;
  - V6.4 first-column anchoring;
  - V6.4 removal of `Next Step:` and `Show:` visible label prefixes;
  - V6.5 central theme token system;
  - V6.6 amber/green action colour semantics;
  - V6.6 scrollbar thickness;
  - V6.6 centred single-frame steering slider;
  - V6.7 Bulk Edit Selected Frames panel and one-field-at-a-time edit safety;
  - V6.8 traceable soft-delete / hidden-frame behaviour.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_8_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Data page bulk-edit flow, edit service, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a focused temporary-session batch-edit test with 1,000 JSONL rows and 500 selected frames, confirming:
  - selected steering rows were updated in both `labels.jsonl` and `records.jsonl`;
  - non-selected rows were left unchanged;
  - speed/throttle values were preserved during steering-only edits;
  - steering values were preserved during speed-only edits;
  - the batch path changed the expected number of metadata rows.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.9`;
  - `PATCH_VERSION` reports `piTrainer_0_6_9`;
  - `FORMAT_VERSION` reports `0_6_9_fast_bulk_edit_jsonl_batches`.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6+0.6.7+0.6.8 to identify only intended changed/new files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run because this patch targets JSONL label editing speed only.

## Known limits / next steps
- Bulk editing still rewrites the affected JSONL files once per action, because JSONL cannot safely update arbitrary lines in place when record lengths change.
- There is still no undo/unhide-style history panel for bulk label edits. The existing warning checkbox and confirmation dialog remain the safety mechanism.
