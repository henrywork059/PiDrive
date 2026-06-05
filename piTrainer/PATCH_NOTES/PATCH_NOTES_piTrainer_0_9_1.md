# PATCH NOTES — piTrainer_0_9_1 Session Working Folder + Playback/Table Readability Patch

## Request summary

Patch v9 so that:

- when a session is loaded, piTrainer treats the loaded session folder as the working folder;
- preprocess save/settings output, trained-model save output, and export output all default to that same folder;
- the Data Review playback maximum increases from 100 FPS to 250 FPS;
- the record list table is easier to read with stronger alternating row colours and a highly visible selected row.

## Cause / root cause

The v9 baseline still kept several save destinations independent from the loaded session:

- preprocess save operations wrote under `state.out_dir_path`, which came from `state.export_config.out_dir`;
- Export used `Export Options > Output directory`, also backed by `state.export_config.out_dir`;
- Train used its own saved model directory field, restored from `QSettings`.

That meant loading a session did not automatically make the session folder the common working/output folder. The user had to manually point multiple pages at the session folder.

The playback FPS limit was simply the UI spin-box range in `PlaybackControlPanel`.

The record table already had alternating rows enabled, but the v9 stylesheet mainly styled `QTableWidget`; the Data page record list is a `QTableView`, so its alternating and selected-row contrast was not strong enough.

## Files changed

- `piTrainer/piTrainer/main_window.py`
  - Adds loaded-session working-folder resolution.
  - Syncs preprocess/export output path and trained-model save path after session load.
- `piTrainer/piTrainer/pages/data_page.py`
  - Calls the working-folder sync immediately after selected sessions are loaded.
- `piTrainer/piTrainer/pages/preprocess_page.py`
  - Adds a working-folder change hook and logs the active preprocess save/settings folder.
- `piTrainer/piTrainer/pages/train_page.py`
  - Adds a page-level setter for the trained-model save folder.
- `piTrainer/piTrainer/pages/export_page.py`
  - Adds a page-level setter for the export output folder.
- `piTrainer/piTrainer/panels/export/export_options_panel.py`
  - Adds a setter that updates both the visible output-directory field and `state.export_config.out_dir`.
- `piTrainer/piTrainer/panels/data/playback_control_panel.py`
  - Raises the playback FPS control maximum from `100.0` to `250.0`.
- `piTrainer/piTrainer/panels/data/preview_panel.py`
  - Names the record table `recordPreviewTable` for targeted styling.
  - Clamps playback FPS internally to `250.0` as a backend safety guard.
- `piTrainer/piTrainer/ui/styles.py`
  - Extends table styling to `QTableView`.
  - Adds stronger alternating row colour for the Data record preview table.
  - Adds amber/high-contrast selected-row styling for the Data record preview table.
- `piTrainer/piTrainer/security/version_gate.py`
  - Supports `minimum_version` so v9 patch builds such as `0.9.1` are not blocked when the manifest minimum remains `0.9.0`.
  - Keeps lower versions blocked when they are older than `minimum_version`.
- `piTrainer/piTrainer/version.py`
  - Updates the visible version to `0.9.1 / piTrainer_0_9_1`.
- `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_9_1.md`
  - This patch note.

## Exact behavior changed

### Session working folder

After loading selected sessions from the Data page:

- if exactly one session is selected, piTrainer resolves the real session folder with the existing session resolver and uses that folder as the working folder;
- preprocess save/settings operations now use that folder through `state.out_dir_path`;
- `Save Trained Model` now defaults to that folder;
- `Export Options > Output directory` now updates to that folder;
- exported `.keras` / `.tflite` files now default to that folder;
- the Train and Export visible path fields are updated immediately after session load.

If multiple sessions are loaded at once, there is no single session folder, so piTrainer uses the records root as the common working folder rather than silently choosing one of the sessions.

### Playback FPS

- Data Review playback speed range is now `0.5` to `250.0` FPS.
- The preview playback timer also clamps requested FPS to `250.0` so code-side calls cannot accidentally exceed the new intended maximum.

### Record list readability

- The Data page record preview table now has a targeted object name: `recordPreviewTable`.
- Adjacent rows use a stronger alternate background.
- The selected/current row uses an amber high-contrast selection colour so the current row is much easier to see.

### Version gate compatibility

- `minimum_version` is now honored directly.
- Versions older than `minimum_version` are blocked.
- Versions equal to or newer than `minimum_version` are allowed even if the older `allowed_versions` list has not yet been expanded for every v9 patch.
- Explicit `blocked_versions` still wins first.

## Behavior intentionally not changed

- No training algorithm changed.
- No preprocessing recipe logic changed.
- No export conversion logic changed.
- No TFLite output ordering changed.
- No dataset row loading/parsing logic changed.
- No session folder naming or scanning rules changed.
- Existing manual Browse controls for model/export paths still work after loading a session.
- Existing V9 reliable one-folder EXE packaging files were not changed.

## Compatibility / rollback safety

- Built forward from `piTrainer_0_9_0`.
- Checked the latest and previous relevant patch notes before finalizing:
  - `PATCH_NOTES_piTrainer_0_9_0.md`
  - `PATCH_NOTES_piTrainer_0_8_15.md`
  - `PATCH_NOTES_piTrainer_0_8_13.md`
  - `PATCH_NOTES_piTrainer_0_8_12.md`
- Confirmed this patch does not intentionally roll back:
  - v9 version-gate baseline behavior;
  - reliability-first EXE packaging from `0.8.15`;
  - TensorFlow/Keras training packaging support from `0.8.13`;
  - `unittest` startup packaging fix from `0.8.12`;
  - v8/v9 Data page selection, sorting, preview, and playback behavior.

## Verification actually performed

- Inspected the real v9 files from `piTrainer_0_9_0_.zip`.
- Confirmed the real app entry point remains `piTrainer/main.py`.
- Inspected the session loader and resolver before wiring the working folder.
- Confirmed preprocess save/settings and export output both depend on `state.export_config.out_dir` / `state.out_dir_path`.
- Confirmed trained-model saving uses the Train page save-dir control and added a direct sync path for it.
- Ran Python syntax compilation:
  - `python3 -m compileall -q piTrainer main.py`
- Ran AST parsing over all Python files under `piTrainer/` successfully.
- Tested the updated version-gate evaluator against a manifest with:
  - `minimum_version: 0.9.0`
  - `allowed_versions: [0.9.0]`
- Confirmed the version-gate evaluator blocks `0.8.15` and allows `0.9.0`, `0.9.1`, and `0.10.0`.
- Verified the patch package contains only changed files plus this patch note.

## Verification not performed

- Live PySide6 GUI clicking was not run in this Linux sandbox.
- Windows EXE rebuild was not run in this sandbox.
- Real playback timing at 250 FPS was not hardware/display tested here.

## Known limits / next steps

- With multiple sessions loaded together, piTrainer uses the records root as the common output folder because there is no single session folder.
- Very high playback FPS depends on PC speed, image size, and UI refresh load; the control now allows 250 FPS, but real smoothness depends on the machine.
