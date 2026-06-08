# PiSD 0.10.10 Patch Notes

## Request summary

The user decided the experimental PiSD `0_10_9` frame ID naming was too complicated and requested a return to the original frame ID format.

This patch restores the original recording filename / frame-id behaviour while preserving the accepted `0_10_9` preview-button placement fixes.

## Baseline and anti-rollback source

This patch was built forward from:

1. `PiSD_0_10_0.zip`
2. accepted patches `PiSD_0_10_1_patch.zip` through `PiSD_0_10_9_patch.zip`

The patch was checked against the latest patch note and the previous accepted patch notes (`0_10_6`, `0_10_7`, `0_10_8`, and `0_10_9`) to avoid rolling back:

- AI Mode `Limiter / correction / manual` three-pane panel
- one visible `Save AI settings` button outside toggled panes
- AI Mode recording download panel
- global Space STOP
- AI Mode max-throttle persistence
- Manual Drive and AI Mode `r` / `s` shortcuts
- additive correction equation: `AI + manual * Correction %`
- fixed-throttle-after-correction behaviour
- `0_10_9` top-of-preview button placement on Manual Drive, AI Mode, Dashboard, and Testing Server

## Cause / root cause

`0_10_9` changed frame IDs and image filenames to a longer global format:

```text
pisd_<session/date>_f000001_<utc-stamp>_<uuid>.jpg
```

That made cross-session identity clearer, but it also made the visible filenames and trainer workflow more complicated. The user preferred the simpler original format.

## Files changed

- `pisd/services/recording_service.py`
  - Removed the `0_10_9` `_make_frame_identity()` helper.
  - Restored the original filename style:

    ```text
    frame_000001_<utc-stamp>_<uuid>.jpg
    ```

  - Restored the original `records.jsonl` frame-id style:

    ```text
    <session_id>_000001_<utc-stamp>_<uuid>
    ```

  - Removed new `frame_id_scheme` and `frame_id_unique_scope` fields from new records and overlay history entries.
  - Restored compact `labels.jsonl` output without extra global-id fields.

- `scripts/test_recording_service.py`
  - Restored recording-service tests to validate the original simpler filename/label schema.

- `pisd/__init__.py`
  - Updated version to `0.10.10`.

- `README.md`
  - Updated current version to `PiSD_0_10_10`.
  - Added `0.10.10` behaviour notes.

- `docs/RECORDING_DATA.md`
  - Restored examples to the original `frame_000001_<stamp>_<uuid>.jpg` style.
  - Removed wording that described the experimental `0_10_9` global frame-id format as the current behaviour.

- `docs/STABLE_BASELINE.md`
  - Added the `0.10.10` forward-patch note.

- `docs/TEST_PLAN.md`
  - Added `0.10.10` verification steps.

- `docs/AI_MODE_CODE_MAP.md`
  - Added a note that the frame-id restore does not change AI Mode control wiring.

## Exact behavior changed

New recordings and snapshots now use the original visible image filename format again:

```text
frame_000001_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
frame_000002_YYYYMMDDTHHMMSSffffffZ_xxxxxxxx.jpg
```

Full `records.jsonl` entries still include:

```text
frame_id
frame_index
saved_at_utc
session_id
relative_file
camera_settings
motor_state
steering
throttle
training_label
overlay_settings
```

But new records no longer include the experimental fields:

```text
frame_id_scheme
frame_id_unique_scope
```

New `labels.jsonl` entries return to the original compact trainer-facing schema:

```text
frame
relative_file
steering
throttle
timestamp_utc
source_frame_seq
session_id
overlay_settings
overlay_settings_file
overlay_settings_history_file
overlay_schema_version
```

## Compatibility / trade-off

This intentionally returns to the simpler original workflow. If frames from different sessions are compared or merged later, use the folder path, `session_id`, and `timestamp_utc` as context instead of relying on a new global ID field in `labels.jsonl`.

Existing recordings made with `0_10_9` are not modified. They can still be read as saved data, but new captures after this patch use the restored original format.

## Verification actually performed

The patch was applied over a clean extracted `PiSD_0_10_0.zip` plus accepted patches `0_10_1` through `0_10_9`, then these checks were run:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/main_dashboard.js
node --check pisd/web/static/js/testing_server.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_testing_server_gui.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All checks above passed.

The recording-service test output was also inspected and confirmed:

- saved image names use `frame_000001_<stamp>_<uuid>.jpg`
- `records.jsonl` keeps `frame_id` and `frame_index`
- `labels.jsonl` uses the compact original trainer label shape
- no new `frame_id_scheme` field is written by the restored path

## Known limits / next steps

Not hardware-verified in this container:

- real Pi camera capture
- real Manual Drive / AI Mode recording from the browser
- real zip download of a new recording folder
- real Pi Chromium preview-button layout
- real piTrainer import of newly restored-format recordings
- real motor STOP response
- real AI inference

The duplicate/cross-session frame identity concern from `0_10_9` is intentionally not solved in this patch because the requested direction was to restore the original frame ID format.
