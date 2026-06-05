# PATCH NOTES — piTrainer_0_9_2 Data Delete/Recover + Filter Split Patch

## Request summary

Patch v9 so that the Data Workflow Manage area is split into clearer workflow panels:

- `2 Delete and Recover`
- `3 Filter`
- existing review actions move forward to `4 Review`

Also update Data Control so it supports:

- deleting/hiding selected frames from training;
- recovering/unhiding the last hidden frame(s);
- recovering/unhiding all hidden frames;
- a hidden true-delete cleanup shortcut: `Ctrl+Z, D` / `Ctrl+Z, Ctrl+D`.

## Cause / root cause

The v9 Data Workflow previously grouped hiding/deleting and filtering inside one `2 Manage` tab. That made two different types of action appear together:

- destructive or reversible data-visibility actions;
- non-destructive preview filtering.

The previous hide/delete implementation already used soft-delete JSONL flags, but there was no UI action to remove those flags and recover hidden rows after the user changed their mind. The soft-delete metadata also meant a permanent cleanup path could be added safely by targeting only rows that were already hidden.

## Files changed

- `piTrainer/piTrainer/pages/data_page.py`
  - Splits the Data Workflow tabs into `2 Delete and Recover`, `3 Filter`, and `4 Review`.
  - Wires the Delete/Recover panel to hide, recover-last, recover-all, and hidden permanent-cleanup actions.
  - Reloads the selected sessions after recovery or permanent cleanup so the preview table reflects the JSONL state immediately.
- `piTrainer/piTrainer/panels/data/data_control_panel.py`
  - Renames the panel to `Delete and Recover`.
  - Keeps the existing confirm checkbox and delete/hide button.
  - Adds a numeric `Last X frame(s)` recover control.
  - Adds `Recover Last` and `Recover All Hidden Frames` actions.
- `piTrainer/piTrainer/services/data/delete_service.py`
  - Adds recovery logic that removes piTrainer hidden/delete trace flags from JSONL rows.
  - Adds permanent cleanup logic for hidden rows.
  - Permanent cleanup removes hidden JSONL rows and deletes unreferenced image files only when they are inside the loaded session/records root.
  - Keeps visible image files if they are still referenced by non-hidden rows.
- `piTrainer/piTrainer/services/data/visibility_service.py`
  - Adds helper functions for reading hide timestamps and removing piTrainer hidden/delete trace flags.
- `piTrainer/piTrainer/main_window.py`
  - Adds hidden permanent-cleanup shortcut support for `Ctrl+Z, D` and `Ctrl+Z, Ctrl+D`.
  - Does not expose this shortcut in the normal shortcuts help list.
- `piTrainer/piTrainer/version.py`
  - Updates the visible version to `0.9.2 / piTrainer_0_9_2`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_2.md`
  - This patch note.

## Exact behavior changed

### Data Workflow tabs

The Data Workflow tab layout is now:

1. `1 Load`
2. `2 Delete and Recover`
3. `3 Filter`
4. `4 Review`

The Filter panel is no longer inside the delete/manage panel. Filtering remains non-destructive and still controls the preview rows before review, editing, deletion, plotting, preprocessing, or training.

### Delete / hide selected frames

The existing soft-delete behavior is preserved:

- selected preview rows are hidden from training by writing traceable JSONL flags;
- JSONL rows are not removed;
- image files are not removed;
- hidden rows are skipped by the loader and training/validation guards.

### Recover hidden frames

The `Delete and Recover` panel now has two recovery modes:

- `Recover Last`: recover/unhide the last X hidden frame(s), using the value in the spin box;
- `Recover All Hidden Frames`: recover/unhide all hidden frames in the loaded/selected session(s).

Recovery removes piTrainer's hide/delete trace flags from matching `labels.jsonl` / `records.jsonl` rows and reloads the selected session(s). It does not modify or delete image files.

### Hidden permanent cleanup shortcut

The hidden cleanup action is available through:

- `Ctrl+Z, D`
- `Ctrl+Z, Ctrl+D`

This action:

- asks for confirmation before changing files;
- permanently removes JSONL rows that are already hidden;
- deletes image files for those hidden rows only when the images are inside the loaded session/records root;
- keeps image files that are still referenced by visible rows;
- reloads the selected sessions after cleanup.

## Behavior intentionally not changed

- No training, validation, preprocessing, export, or TFLite conversion logic changed.
- The existing soft-delete/hide selected-frame behavior remains the normal visible delete action.
- The hidden permanent cleanup is not exposed as a normal button.
- The v9.1 session working-folder behavior is preserved.
- The v9.1 playback FPS limit of 250 is preserved.
- The v9.1 record-table alternating-row and selected-row styling is preserved.
- Existing bulk edit, merge sessions, overlay controls, preview table selection, playback, and filters are preserved.

## Compatibility / rollback safety

- Built forward from the accepted `piTrainer_0_9_1` patch state, not from raw `0.9.0` alone.
- Checked the latest and previous relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_9_1.md`
  - `PATCH_NOTES_piTrainer_0_9_0.md`
  - `PATCH_NOTES_piTrainer_0_8_15.md`
  - `PATCH_NOTES_piTrainer_0_8_13.md`
- Confirmed this patch does not intentionally roll back:
  - session working-folder sync from `0.9.1`;
  - playback FPS max 250 from `0.9.1`;
  - table readability styling from `0.9.1`;
  - v9 version-gate compatibility from `0.9.1`;
  - v9 stable baseline/version naming from `0.9.0`;
  - reliable one-folder EXE packaging from `0.8.15`.

## Verification actually performed

- Applied `piTrainer_0_9_1_patch.zip` over `piTrainer_0_9_0_.zip` before making this patch.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Ran a local service-level soft-delete/recover/permanent-cleanup test using a temporary fake session with `labels.jsonl` and image files:
  - loaded 3 rows;
  - hid 1 selected frame;
  - confirmed loader returned 2 visible rows;
  - recovered 1 hidden frame;
  - confirmed loader returned 3 visible rows;
  - hid the frame again;
  - permanently purged hidden data;
  - confirmed the hidden JSONL row and unreferenced image file were removed;
  - confirmed loader returned 2 visible rows.
- Re-ran compileall after changes.
- Inspected the patch diff to confirm only targeted files changed.
- Packaged only changed files plus this patch note.

## Known limits / next steps

- `Recover Last X` sorts hidden rows by piTrainer's `hidden_at_utc` timestamp. If many frames were hidden in the same batch and therefore share the same timestamp, file/read order is used as the tie-breaker.
- Permanent cleanup is intentionally conservative: it skips deleting image files outside the loaded session folders or files still referenced by visible rows.
- The hidden permanent-cleanup shortcut still shows a confirmation dialog to reduce accidental irreversible deletion.
