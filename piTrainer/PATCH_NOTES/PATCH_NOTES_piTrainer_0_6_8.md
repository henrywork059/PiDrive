# PATCH NOTES — piTrainer_0_6_8 Soft Delete / Hidden Training Rows Patch

## Request summary
- Deletion is taking too long when multiple frames are selected.
- Replace physical frame deletion with a traceable hidden-flag workflow.
- Do not delete frame image files or remove JSONL data rows.
- Add flags to the selected frames/data so they become hidden.
- Make sure hidden frames/data are not used to train the model.

## Cause / root cause
The previous delete workflow deleted selected frames one by one. Each selected frame could trigger a separate scan/rewrite of `labels.jsonl` and `records.jsonl`, and it also attempted to remove the image file from disk. That makes multi-frame deletion slow on large PiSD sessions and removes useful audit/recovery information.

A safer and faster approach is a soft-delete workflow:

- scan each affected session JSONL file once per delete action;
- keep the source row in place;
- keep the image file in place;
- mark matching metadata rows with traceable hidden flags;
- hide those rows from the active UI and all training data flows.

## Files changed
- `piTrainer/piTrainer/services/data/visibility_service.py`
  - New shared hidden-row helper service.
  - Defines hidden/deleted flag keys.
  - Adds `mark_record_hidden()` to write traceable flags.
  - Adds `is_record_hidden()` for raw JSONL records.
  - Adds `without_hidden_rows()` for DataFrame-level final guards.
- `piTrainer/piTrainer/services/data/delete_service.py`
  - Replaces physical row/image deletion with batch soft-delete/hide logic.
  - Adds `hide_frames_from_training()` to group selected records by session and scan each JSONL file once.
  - Keeps a backward-compatible `delete_frame_from_session()` wrapper, now implemented as soft-delete.
  - Removes image-file `unlink()` behaviour.
- `piTrainer/piTrainer/services/data/record_loader_service.py`
  - Skips hidden records when loading `labels.jsonl` and fallback `records.jsonl` rows.
  - Tracks hidden label identities so a hidden `labels.jsonl` row is not reintroduced from fallback `records.jsonl`.
- `piTrainer/piTrainer/pages/data_page.py`
  - Changes selected-frame deletion to call the batch hidden-flag service.
  - Removes selected rows from loaded DataFrames immediately instead of reloading all sessions after each delete action.
  - Updates stats, plot, preview, training split state, and validation split state after hiding rows.
  - Updates user-facing wording from physical delete to hide/delete where needed.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Updates help text, checkbox text, tooltip, and button label to explain that rows/images are kept and hidden flags are added.
- `piTrainer/piTrainer/services/preprocess/preprocess_service.py`
  - Adds a hidden-row guard before preprocessing filters and augmentation.
- `piTrainer/piTrainer/pages/train_page.py`
  - Adds a hidden-row guard in `_usable_training_rows()` before train/validation rows are accepted.
- `piTrainer/piTrainer/services/train/dataset_service.py`
  - Adds a final hidden-row guard before TensorFlow dataset creation.
- `piTrainer/piTrainer/pages/validation_page.py`
  - Adds a hidden-row guard before validation dataset selection is returned.
- `piTrainer/piTrainer/main_window.py`
  - Updates shortcut help text so `Delete` is described as hiding selected rows from training.
- `piTrainer/piTrainer/ui/formatting.py`
  - Updates `FORMAT_VERSION` to `0_6_8_soft_delete_hidden_training_rows`.
- `piTrainer/piTrainer/version.py`
  - Updates visible version metadata to `0.6.8` / `piTrainer_0_6_8`.
- `piTrainer/DOCS/FORMAT_AND_STYLE_GUIDE.md`
  - Documents soft-delete / hidden-frame rules.
- `piTrainer/AGENTS.md`
  - Updates future AI-agent instructions to preserve traceable hidden-row handling.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_6_8.md`
  - This patch note.

## Exact behaviour changed
- `Data Workflow > 2 Manage > Data Control` now labels the action as `Hide Selected Frame(s)`.
- The Delete key still works on selected Record Preview rows after the Data Control checkbox is ticked, but it now hides rows instead of deleting files.
- Selected rows are marked in matching JSONL records using traceable flags, including:
  - `hidden_from_training: true`
  - `piTrainer_hidden: true`
  - `deleted_by_pitrainer: true`
  - `hidden_reason`
  - `hidden_at_utc`
  - `hidden_source`
  - `hidden_action`
- If a source row contains a nested `training_label` dictionary, the same flags are mirrored into it.
- Image files are not removed.
- JSONL rows are not removed.
- Multi-frame hide/delete is faster because each affected `labels.jsonl` / `records.jsonl` file is scanned and rewritten once per action rather than once per selected frame.
- Hidden selected rows disappear from the active Record Preview immediately.
- Hidden rows are removed from loaded `dataset_df`, `filtered_df`, `train_df`, `val_df`, and the current preview source DataFrame.
- Future session loads skip hidden rows.
- Preprocess, Train, Validation, and TensorFlow dataset creation all apply hidden-row guards so hidden frames do not train or validate the model.

## Behaviour intentionally not changed
- Data Workflow remains ordered as `1 Load`, `2 Manage`, `3 Review`.
- Data Review remains ordered as `1 Records`, `2 Stats`, `3 Plot`.
- Frame Filter remains in `2 Manage`.
- Bulk Edit Selected Frames remains in `3 Review` and remains expanded by default.
- Merge Sessions remains in `3 Review` and collapsed by default.
- Data Control remains expanded by default.
- The Data Control confirmation checkbox remains required before Delete/Hide actions run.
- Repeated hide/delete actions do not open a repeated confirmation popup after the checkbox is ticked.
- `frame_id` remains the first Record Preview column.
- Record Preview multi-selection and first-column anchoring remain unchanged.
- Playback controls remain directly under the image preview.
- Single-frame and bulk steering/speed edit workflows remain unchanged.
- PiSD V7 `labels.jsonl` / `records.jsonl` loading remains the primary supported data path.
- PiSD V7 overlay redraw and overlay metadata support remain unchanged.
- V6.6 colour semantics, scrollbar thickness, splitter handle thickness, and centred steering sliders remain unchanged.

## Compatibility notes
- This is a patch-only zip. It overlays changed/new files into an existing V6 + accepted `0.6.1` through `0.6.7` install.
- Existing source sessions do not need migration. Hidden flags are added only when the user hides selected frames.
- Existing hidden-like keys are respected by the loader and final guards when they are truthy, including `hidden_from_training`, `piTrainer_hidden`, `excluded_from_training`, `deleted_by_pitrainer`, `deleted`, and `hidden`.
- The old `delete_frame_from_session()` function name is kept as a compatibility wrapper, but it now performs a soft delete.
- This patch does not add a permanent purge tool. A future purge tool could be added separately if the user later wants true file removal.

## Rollback-risk check
- Built forward from `piTrainer_0_6_0` with accepted `0_6_1` through `0_6_7` patches applied first.
- Checked the real entry point:
  - `piTrainer/main.py`
- Checked latest and previous relevant piTrainer patch notes before editing:
  - `PATCH_NOTES_piTrainer_0_6_7.md`
  - `PATCH_NOTES_piTrainer_0_6_6.md`
  - `PATCH_NOTES_piTrainer_0_6_5.md`
  - `PATCH_NOTES_piTrainer_0_6_4.md`
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
  - V6.7 Bulk Edit Selected Frames panel and one-field-at-a-time edit safety.

## Verification actually performed
- Applied `piTrainer_0_6_1_patch.zip` through `piTrainer_0_6_7_patch.zip` over a fresh `piTrainer_0_6_0` tree before editing.
- Inspected current Data page, Data Control panel, delete service, record loader, training/preprocess/validation data paths, latest patch notes, style guide, and AI-agent instructions.
- Ran:
  - `python3 -m compileall -q main.py piTrainer`
- Ran AST parsing over all Python files successfully.
- Ran a focused temporary-session soft-delete check confirming:
  - selected rows are flagged in both `labels.jsonl` and `records.jsonl`;
  - source image files remain on disk;
  - future `load_records_dataframe()` calls skip the hidden row;
  - `without_hidden_rows()` removes hidden rows from DataFrames.
- Ran a fallback safety check confirming:
  - a row hidden in `labels.jsonl` is not reintroduced through fallback `records.jsonl` loading.
- Ran static source checks confirming:
  - `APP_VERSION` reports `0.6.8`;
  - `PATCH_VERSION` reports `piTrainer_0_6_8`;
  - `FORMAT_VERSION` reports `0_6_8_soft_delete_hidden_training_rows`;
  - the new delete service no longer calls image-file `unlink()`.
- Compared the working tree against fresh V6+0.6.1+0.6.2+0.6.3+0.6.4+0.6.5+0.6.6+0.6.7 to identify only intended changed/new files.
- Removed generated `__pycache__` folders before packaging.

## Verification not performed
- Live Windows/PySide6 GUI rendering was not run in this sandbox.
- Real PiSD recording import was not re-run in this sandbox.
- Full TensorFlow training was not run, but the loader, preprocessing, train-page filtering, validation dataset selection, and TensorFlow dataset creation paths now include hidden-row guards.

## Known limits / next steps
- Hidden rows are not shown in the active Record Preview. There is no UI yet to list or unhide soft-deleted frames.
- If the user wants recovery/unhide later, add a dedicated `Hidden Frames` management panel rather than mixing hidden rows back into the normal training table.
- If the user wants permanent cleanup later, add a separate purge action with stronger warning text so it is clearly different from this safe soft-delete workflow.
