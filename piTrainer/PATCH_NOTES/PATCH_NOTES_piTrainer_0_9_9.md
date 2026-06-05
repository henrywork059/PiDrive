# PATCH NOTES — piTrainer_0_9_9 Preprocess Completion and Defaults Patch

## Request summary

Improve the Preprocess workflow so the user can clearly see when preprocessing has finished. Also change the default preprocessing source/mode so the normal workflow starts from selected-session visible table rows and uses all modes by default.

## Cause / root cause

The previous Preprocess page mainly reported completion through the status bar and the text preview area. That made it too easy to miss whether preprocessing was only previewed or actually applied.

The previous source/mode defaults also leaned toward the older manual-row training preference. The Preprocess filter refreshed its mode from `TrainConfig.only_manual`, so the mode could silently return to `Manual only` when the user expected all loaded modes. The source choices were also worded as generic loaded/current filtered rows instead of matching the visible selected-session workflow.

## Files changed

- `piTrainer/piTrainer/app_state.py`
  - Changes the default training/data-load manual preference to `False`, so a fresh app starts from all modes instead of preferring manual rows.
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Uses the Data page's current visible Records table rows as the default preprocessing source.
  - Falls back safely to the active loaded dataframe if the table has no visible dataframe yet.
  - Adds explicit status updates for idle, preview, running, skipped, reset, and completed states.
  - Shows a clear done message after applying/auto-preprocessing.
- `piTrainer/piTrainer/panels/preprocess/preprocess_filter_panel.py`
  - Renames source options to shorter, clearer choices: `Visible table rows` and `All loaded rows`.
  - Defaults source to `Visible table rows`.
  - Defaults mode to `Any mode`.
  - Stops Preprocess refreshes from silently changing mode back to Train's manual preference.
  - Keeps backward compatibility for older saved recipe values such as `Current filtered rows` and `Loaded dataset (all rows)`.
- `piTrainer/piTrainer/panels/preprocess/preprocess_result_panel.py`
  - Adds a persistent status banner above the preview text.
  - Adds helper methods for idle/running/preview/done/warning states.
- `piTrainer/piTrainer/ui/styles.py`
  - Adds status-banner styling for Preprocess states.
- `piTrainer/piTrainer/version.py`
  - Updates visible version to `0.9.9 / piTrainer_0_9_9`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_9.md`
  - This patch note.

## Exact behavior changed

- A fresh app now defaults to all modes instead of preferring manual rows.
- Preprocess `Source rows` now defaults to `Visible table rows`.
  - This means the default source follows the selected sessions and the currently visible Data Records table rows.
  - If the Data table is not available yet, it falls back to the active loaded dataframe.
- Preprocess `Mode filter` now defaults to `Any mode`.
- Preprocess refreshes no longer override the user's selected source/mode filter.
- The Preprocess Output panel now has a visible status banner:
  - idle: source is ready or sessions need loading;
  - preview: counts were previewed but not applied;
  - running: auto preprocess has started;
  - warning: no source rows were available;
  - done: preprocessing was applied and rows are ready for training.
- After Auto Preprocess or Apply finishes, the banner shows:
  - `✓ PREPROCESS DONE — ... active row(s) ready for training ...`

## Behavior intentionally not changed

- The actual preprocessing recipe logic is unchanged.
- Image filtering, duplicate-image filtering, frame stride, range filters, straight balancing, turn boosting, horizontal flipping, color variants, and image resizing are unchanged.
- Existing saved recipe files still load where possible; older source-mode names are normalized to the new names.
- The `0.9.1` session working-folder behavior is preserved.
- The `0.9.1` playback FPS maximum of `250` is preserved.
- The `0.9.2` Hide & Recover workflow and hidden permanent-delete shortcut are preserved.
- The `0.9.5` Image Preview Up/Down navigation focus fix is preserved.
- The `0.9.6` through `0.9.8` model deploy feature, tab order, and packaging repair are preserved.

## Rollback-risk check

Checked against the latest current code state plus the latest v9 patch notes:

- `PATCH_NOTES_piTrainer_0_9_8.md`
- `PATCH_NOTES_piTrainer_0_9_7.md`
- `PATCH_NOTES_piTrainer_0_9_6.md`
- `PATCH_NOTES_piTrainer_0_9_5.md`

Confirmed this patch is forward-only and does not remove the deploy files, deploy tab order, arrow-navigation fix, hide/recover logic, or working-folder behavior from previous accepted v9 patches.

## Verification actually performed

- Built this patch on top of the accepted `0.9.8` working state.
- Inspected the existing Preprocess page, Preprocess filter panel, Data page visible-table flow, Train config default, and result panel before patching.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Parsed all Python files under `piTrainer/` with `ast.parse` successfully.
- Verified the version file reports `0.9.9 / piTrainer_0_9_9`.
- Prepared a patch-only zip with only changed files and this patch note.

## Verification not performed

- Live Windows PySide6 GUI clicking was not run in this Linux sandbox.
- PySide6 visual rendering of the new status banner was not run because this sandbox does not have PySide6 installed.
- A PyInstaller / EXE rebuild was not run for this targeted patch.

## Known limits / next steps

- The default source follows the current Data Records table rows. If the Data table has been filtered, preprocessing uses those visible rows by default. Change `Source rows` to `All loaded rows` when the full selected-session dataset should be used instead.
- The Train page still has a manual-row preference checkbox, but it is now off by default for a fresh app.
