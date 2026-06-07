# PATCH NOTES — piTrainer_0_9_11 Data Page Maintainability Refactor

## Request summary

Review the app code and make it easier to manage by splitting large scripts into smaller, focused files.

## Cause / root cause

The current Data page had grown to roughly 1,000 lines. It was handling too many responsibilities in one file:

- Data Workflow layout assembly
- session scanning/loading/focus
- filtering and overlay state
- single-frame and bulk editing
- model deployment and diff sorting
- playback controls
- hide/recover/permanent-delete actions
- shared record identity helpers

That made later patches more risky because small changes to one workflow required editing a very large mixed-responsibility file.

## Files changed

- `piTrainer/piTrainer/pages/data_page.py`
  - Reduced to a thin Data page assembly class.
  - Keeps the same public `DataPage` entry point used by `main_window.py`.
  - Builds the panels, workflow tabs, splitters, timers, and callback wiring.
- `piTrainer/piTrainer/pages/data_page_support.py`
  - New shared helper mixin for record identity, source-record lookup, dataframe text helpers, plot refresh, and state refresh.
- `piTrainer/piTrainer/pages/data_page_sessions.py`
  - New session workflow mixin for scanning sessions, loading selected sessions, focusing records, and merging sessions.
- `piTrainer/piTrainer/pages/data_page_filter_edit.py`
  - New filter/edit mixin for visible-row filtering, overlay toggles, preview selection, image edits, and bulk edits.
- `piTrainer/piTrainer/pages/data_page_deploy.py`
  - New deploy mixin for model deployment, prediction-field merge, diff sorting, and applying AI output to selected rows.
- `piTrainer/piTrainer/pages/data_page_playback.py`
  - New playback mixin for start/stop/restart and FPS/position callbacks.
- `piTrainer/piTrainer/pages/data_page_visibility.py`
  - New hide/recover mixin for hiding selected frames, recovering hidden frames, and hidden permanent delete.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.11 / piTrainer_0_9_11`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_11.md`
  - Adds this patch note.

## Exact behavior changed

No user-facing workflow behavior was intentionally changed.

The structural change is:

- `data_page.py` is reduced from about 1,000 lines to about 170 lines.
- Data page behavior is now divided by responsibility across smaller scripts.
- Existing callbacks and method names are preserved through mixins, so other app code can still call the same Data page methods.

## Behavior intentionally preserved

This patch is a maintainability refactor only. It preserves:

- `0.9.1` session working-folder behavior.
- `0.9.1` max playback FPS of `250`.
- `0.9.2` Hide/Recover workflow and hidden permanent-delete shortcut.
- `0.9.3` / `0.9.4` wording and table-header cleanup.
- `0.9.5` Up/Down navigation after editing.
- `0.9.6` model deployment, output overlay, diff columns, diff sorting, and Apply AI to Selected.
- `0.9.7` tab order with `4 Review` and `5 Deploy`.
- `0.9.8` deploy-file packaging repair.
- `0.9.9` Preprocess done indicator and default source/mode.
- `0.9.10` deploy focus restoration and faster prediction merge.

## Rollback-risk check

Checked the latest current code state and the previous v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_10.md`
- `PATCH_NOTES_piTrainer_0_9_9.md`
- `PATCH_NOTES_piTrainer_0_9_8.md`

Confirmed this patch builds forward from `0.9.10`. It does not replace the Data page with an older copy and does not remove recent Deploy, Preprocess, Hide/Recover, focus, or wording fixes.

## Verification actually performed

- Applied all v9 patches from `0.9.0` through `0.9.10` before refactoring.
- Identified the largest app files and selected `piTrainer/pages/data_page.py` as the highest-impact safe split.
- Confirmed the refactor preserves all 53 existing `DataPage` methods across the new mixin files.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the version file reports `0.9.11 / piTrainer_0_9_11`.
- Prepared a patch-only zip with only changed/new files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI startup was not run in this Linux sandbox because PySide6 is not installed here.
- Real camera/data/model deployment workflows were not run for this structure-only patch.
- A PyInstaller / EXE rebuild was not run.

## Known limits / next steps

- This patch focuses on the Data page because it was the largest and most mixed-responsibility page script. Other large modules such as preview rendering, validation service, overlay service, and styles can be split later in smaller targeted patches.
