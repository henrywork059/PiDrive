# PATCH NOTES — piTrainer_0_9_4 Second UI Text Consistency Patch

## Request summary

Review the visible piTrainer text again and perform the same naming/text optimisation as the previous patch so tab names, panel titles, button names, descriptions, hints, table headers, and status text are precise, consistent, and not too long.

## Cause / root cause

The `0.9.3` wording cleanup removed the most obvious long labels and stale Data Workflow text, but a second pass found more mixed or overly long wording across nearby pages and panels:

- Data still had a few long panel names and less consistent hide/recover text.
- The record table still exposed raw field names such as `frame_id`, `throttle`, `ts`, and `hidden_from_training`.
- Preprocess still mixed longer labels such as `Source Summary`, recipe/setup wording, and verbose action buttons.
- Train, Validate, Export, and TFLite Check pages still had some longer panel titles and repeated action wording.
- Some status messages were correct but longer than needed for normal use.

## Files changed

- `piTrainer/piTrainer/main_window.py`
- `piTrainer/piTrainer/pages/data_page.py`
- `piTrainer/piTrainer/pages/preprocess_page.py`
- `piTrainer/piTrainer/pages/train_page.py`
- `piTrainer/piTrainer/pages/validation_page.py`
- `piTrainer/piTrainer/pages/export_page.py`
- `piTrainer/piTrainer/pages/export_validation_page.py`
- `piTrainer/piTrainer/panels/data/bulk_edit_panel.py`
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
- `piTrainer/piTrainer/panels/data/data_plot_panel.py`
- `piTrainer/piTrainer/panels/data/dataset_stats_panel.py`
- `piTrainer/piTrainer/panels/data/frame_filter_panel.py`
- `piTrainer/piTrainer/panels/data/merge_sessions_panel.py`
- `piTrainer/piTrainer/panels/data/overlay_control_panel.py`
- `piTrainer/piTrainer/panels/data/preview_panel.py`
- `piTrainer/piTrainer/panels/export/export_actions_panel.py`
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
- `piTrainer/piTrainer/panels/export/model_status_panel.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_actions_panel.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_config_panel.py`
- `piTrainer/piTrainer/panels/export_validation/export_validation_summary_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_config_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_filter_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_result_panel.py`
- `piTrainer/piTrainer/panels/preprocess/preprocess_summary_panel.py`
- `piTrainer/piTrainer/panels/train/split_summary_panel.py`
- `piTrainer/piTrainer/panels/train/train_config_panel.py`
- `piTrainer/piTrainer/panels/train/train_control_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_actions_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_config_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_frame_review_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_plot_panel.py`
- `piTrainer/piTrainer/panels/validation/validation_summary_panel.py`
- `piTrainer/piTrainer/version.py`
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_4.md`

## Exact behavior changed

### Data page wording

- Renamed the Data Workflow tab from `2 Hide/Recover` to `2 Hide & Recover`.
- Renamed the Hide/Recover panel to `Hide & Recover`.
- Shortened the hide confirmation checkbox to `Confirm Hide`.
- Shortened recovery actions to `Recover Last` and `Recover All`.
- Shortened hide/recover/permanent-delete dialog titles, status messages, and warnings.
- Shortened filter, merge, overlay, plot, stats, bulk edit, and image-preview labels.
- Changed record table headers from raw field names to readable names, for example:
  - `frame_id` -> `Frame`
  - `frame_number` -> `Frame No.`
  - `throttle` -> `Speed`
  - `ts` -> `Time`
  - `hidden_from_training` -> `Hidden`
- Kept the hidden permanent-delete shortcut hidden and unchanged.

### Preprocess wording

- Shortened workflow/panel names to `Auto`, `Filters`, `Recipe`, `Source`, and `Result` where the surrounding page already gives context.
- Shortened action buttons such as defaults, preview, apply, sync-size, save, refresh, and clean actions.
- Shortened empty-state and summary messages while keeping counts and paths visible.

### Train wording

- Shortened train workflow panel names to `Config`, `Controls`, `Split`, `Train Output`, and `Frame Review`.
- Shortened common action labels such as `Save Model`, `Browse`, and training run status text.
- Kept training configuration behavior unchanged.

### Validate wording

- Shortened validation panel names to `Settings`, `Actions`, `Summary`, `Validate Output`, and `Frame Review`.
- Shortened browse/clear/check wording and result summaries.
- Kept validation metrics and frame review behavior unchanged.

### Export and TFLite Check wording

- Shortened export panels and actions to `Options`, `Model`, `Actions`, and `Export`.
- Shortened TFLite Check panels to `Settings`, `Actions`, `Summary`, `TFLite Output`, and `Frame Review`.
- Standardised TFLite wording around `Check`, while keeping the top-level page name `6 TFLite Check` from `0.9.3`.

## Behavior intentionally not changed

This is a wording-only UI cleanup patch. It does not intentionally change:

- data loading or session working-folder behavior from `0.9.1`;
- playback FPS maximum of `250` from `0.9.1`;
- record table alternating/selected-row styling from `0.9.1`;
- Hide/Recover functionality from `0.9.2`;
- permanent hidden-frame cleanup shortcut behavior from `0.9.2`;
- top-level `6 TFLite Check` naming from `0.9.3`;
- preprocess, train, validate, export, or TFLite calculation logic;
- model architecture, export format, data schema, or runtime config behavior.

## Rollback-risk check

Built forward from the accepted v9 line by applying:

1. `piTrainer_0_9_0_.zip`
2. `piTrainer_0_9_1_patch.zip`
3. `piTrainer_0_9_2_patch.zip`
4. `piTrainer_0_9_3_patch.zip`
5. this `piTrainer_0_9_4` patch

Checked the current and previous relevant patch notes before finalising:

- `PATCH_NOTES_piTrainer_0_9_3.md`
- `PATCH_NOTES_piTrainer_0_9_2.md`
- `PATCH_NOTES_piTrainer_0_9_1.md`
- `PATCH_NOTES_piTrainer_0_9_0.md`

Confirmed this patch does not intentionally roll back the accepted `0.9.1`, `0.9.2`, or `0.9.3` behavior listed above.

## Verification actually performed

- Applied `0.9.1`, `0.9.2`, and `0.9.3` over the uploaded `0.9.0` baseline before making this patch.
- Searched for stale or inconsistent visible wording including:
  - `Delete and Recover`
  - `Confirm hide actions`
  - `Data Workflow > 2 Manage`
  - `2 Manage`
  - `Run Export Validation`
  - `Export Validation`
  - `Training Controls`
  - `Training Config`
  - `Validation Actions`
  - `Validation Config`
  - `Validation Summary`
  - `Source Summary`
  - `Dataset Stats`
  - `Data Control`
- Ran `python3 -m compileall -q piTrainer main.py`.
- Parsed all Python files with `ast.parse`.
- Verified the version reports `0.9.4 / piTrainer_0_9_4`.

## Verification not performed

- Live Windows GUI clicking was not run in this Linux sandbox.
- A PyInstaller / EXE rebuild was not run for this wording-only patch.

## Known limits / next steps

- This patch continues the current direct-string UI style. It does not introduce a central string registry or translation system.
- Some technical terms such as `TFLite`, `.jsonl`, and `Output` are intentionally kept because they are precise and useful in the trainer workflow.
