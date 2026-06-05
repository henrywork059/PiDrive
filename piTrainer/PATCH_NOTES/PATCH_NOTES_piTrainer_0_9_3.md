# PATCH NOTES — piTrainer_0_9_3 UI Wording Consistency Patch

## Request summary

Review and clean up piTrainer UI wording so tab names, button names, descriptions, tooltips, and status messages are more precise, consistent, and not too long.

## Cause / root cause

The `0.9.2` Delete/Recover split worked functionally, but some wording was still too long or inconsistent:

- the new Data workflow used both “Delete and Recover” and “Data Control” wording;
- one confirmation message still pointed to the old `Data Workflow > 2 Manage > Data Control` location;
- visible soft-delete actions mixed the words `Delete`, `Hide`, and `Frame(s)`;
- Export Validation labels were long and repeated across tabs, buttons, panels, and messages;
- several common action buttons used long phrases where the context already explained the action.

## Files changed

- `piTrainer/piTrainer/main_window.py`
  - Shortens main tab tooltip text.
  - Renames the final top-level page from `6 Export Validation` to `6 TFLite Check`.
  - Updates startup/status and shortcut wording to match the shorter page name and new hide confirmation label.
- `piTrainer/piTrainer/pages/data_page.py`
  - Renames `2 Delete and Recover` to `2 Hide/Recover`.
  - Shortens Data Workflow descriptions, panel titles, review tab hints, and Data page summary.
  - Updates stale old-path text from `2 Manage > Data Control` to `2 Hide/Recover`.
  - Shortens hide/recover/permanent-cleanup dialog titles and messages.
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Shortens the Auto workflow action label descriptions and banner tooltip wording.
- `piTrainer/piTrainer/pages/export_page.py`
  - Shortens export next-step text.
  - Updates the post-export TFLite handoff message to point to `TFLite Check`.
- `piTrainer/piTrainer/pages/export_validation_page.py`
  - Renames the user-facing Export Validation page wording to `TFLite Check`.
  - Shortens workflow panel names, result panel names, summary text, next-step text, and log/status messages.
- `piTrainer/piTrainer/panels/data/bulk_edit_panel.py`
  - Shortens bulk-edit panel, confirm checkbox, buttons, and tooltips.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Renames the visible panel to `Hide/Recover`.
  - Shortens help text and recovery action labels.
  - Makes the visible destructive action precise: `Hide Selected`.
- `piTrainer/piTrainer/panels/data/frame_filter_panel.py`
  - Shortens the filter panel title, placeholder, checkbox labels, buttons, and help text.
- `piTrainer/piTrainer/panels/data/overlay_control_panel.py`
  - Shortens overlay checkbox labels while preserving the same overlay options.
- `piTrainer/piTrainer/panels/data/playback_control_panel.py`
  - Shortens playback panel text and changes `Speed (frames/sec)` to `FPS`.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Renames the preview group from `Record Preview` to `Records`.
- `piTrainer/piTrainer/panels/data/session_source_panel.py`
  - Shortens records-root help, placeholder, and session summary messages.
- `piTrainer/piTrainer/panels/export/export_actions_panel.py`
  - Shortens the export action button to `Export`.
- `piTrainer/piTrainer/panels/export_validation/export_validation_actions_panel.py`
  - Shortens TFLite check buttons and panel title.
- `piTrainer/piTrainer/panels/export_validation/export_validation_config_panel.py`
  - Shortens TFLite model/source/settings labels and tooltips.
- `piTrainer/piTrainer/panels/export_validation/export_validation_summary_panel.py`
  - Shortens the summary panel title and empty-result text.
- `piTrainer/piTrainer/panels/preprocess/preprocess_actions_panel.py`
  - Shortens Auto Preprocess, recipe, save, and maintenance action labels.
- `piTrainer/piTrainer/version.py`
  - Updates the visible version to `0.9.3 / piTrainer_0_9_3`.

## Exact behavior changed

### Data wording

- `2 Delete and Recover` is now `2 Hide/Recover`.
- The visible soft-delete button is now `Hide Selected`.
- The confirmation checkbox is now `Confirm hide actions`.
- Recovery buttons are now `Recover Last X` and `Recover All`.
- The filter panel is now simply `Filter`, with `Apply Filter` and `Clear Filter` actions.
- The stale `2 Manage > Data Control` message was removed.

### Export/TFLite wording

- The final workflow page is now named `6 TFLite Check`.
- Export now says the next step is `6 TFLite Check`.
- Exported TFLite validation actions now use `Run Check`, `Check Settings`, and `Check Summary` wording.

### General action wording

- Bulk edit, overlay, playback, session-source, export, and preprocess action labels were shortened.
- Tooltips and status messages were revised where they were too long or referenced old UI locations.

## Behavior intentionally not changed

- No training, validation, preprocessing, export, TFLite conversion, or data parsing logic changed.
- The `0.9.1` session working-folder behavior is preserved.
- The `0.9.1` playback FPS limit of 250 is preserved.
- The `0.9.1` record-table readability styling is preserved.
- The `0.9.2` hide/recover behavior is preserved.
- The `0.9.2` hidden permanent-cleanup shortcut remains hidden and still requires confirmation.
- No runtime config schema or saved user data behavior changed.

## Compatibility / rollback safety

- Built forward from the accepted `piTrainer_0_9_2` state.
- Checked the latest and previous relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_9_2.md`
  - `PATCH_NOTES_piTrainer_0_9_1.md`
  - `PATCH_NOTES_piTrainer_0_9_0.md`
- Confirmed this patch does not intentionally roll back:
  - Data Delete/Recover + Filter split from `0.9.2`;
  - recover last/all hidden frames from `0.9.2`;
  - hidden permanent cleanup shortcut from `0.9.2`;
  - session working-folder sync from `0.9.1`;
  - playback FPS max 250 from `0.9.1`;
  - record-table alternating/selected-row readability from `0.9.1`;
  - version-gate compatibility from `0.9.1`.

## Verification actually performed

- Applied `piTrainer_0_9_1_patch.zip` and `piTrainer_0_9_2_patch.zip` over `piTrainer_0_9_0_.zip` before making this patch.
- Searched for stale UI strings including:
  - `2 Manage`
  - `Data Control`
  - `Delete and Recover`
  - `Delete / Hide`
  - `Export Validation`
  - `Run Export Validation`
  - `Auto Preprocess Active Data`
- Confirmed those stale user-facing strings are removed from active UI files.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Ran AST parsing over Python files under `piTrainer/` successfully.
- Performed a fresh apply test:
  - `0.9.0` baseline + `0.9.1` patch + `0.9.2` patch + `0.9.3` patch
  - confirmed compile passes
  - confirmed version reports `0.9.3 / piTrainer_0_9_3`.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox.
- Windows EXE rebuild was not run in this sandbox.

## Known limits / next steps

- This patch is wording-only. It does not add a translation system or central string registry.
- Some internal class/function/file names still use `ExportValidation` for compatibility; only user-facing wording was changed to `TFLite Check`.
