# PiSD 0.8.11 Patch Notes

## Request summary

The user asked to make sure Manual Drive overlay calibration settings are saved into both recording and snapshot output folders so users can apply the same visual overlay settings later in the training app.

## Root cause / background

PiSD already stored the reduced Manual Drive overlay settings inside `records.jsonl`, `labels.jsonl`, and recording manifests. However, a training app would need to parse JSONL records or labels to recover the same visual calibration. That is less convenient than a stable, session-level sidecar file beside each recording/snapshot folder.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/recording_service.py`
- `PiSD/scripts/test_recording_service.py`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_11.md`

## Behaviour changed

### Recording and snapshot overlay sidecar files

Each recording session folder and each daily snapshot folder now saves:

- `overlay_settings.json`
- `overlay_settings_history.jsonl`

`overlay_settings.json` is the simple trainer-facing file for applying the same Manual Drive visual overlay calibration later. It includes:

- `overlay_schema_version`
- `overlay_settings_source`
- the reduced 7-control `overlay_settings`
- `visual_only: true`
- trainer hint text
- latest frame/session metadata

`overlay_settings_history.jsonl` records the overlay settings used per saved frame. This is useful if the user changes the overlay calibration during a recording session.

### Metadata links added

The following metadata now points to the overlay sidecar files:

- recording `manifest.json`
- snapshot `manifest.json`
- `records.jsonl`
- `labels.jsonl`
- recording library summaries from `/api/recording/items`

The compact `labels.jsonl` entries now include:

- `overlay_settings`
- `overlay_settings_file`
- `overlay_settings_history_file`
- `overlay_schema_version`

This lets piTrainer load either per-frame overlay settings from the labels or the session-level `overlay_settings.json` file.

## Behaviour preserved

- Overlay tuning remains visual-only.
- Overlay settings do not affect motor output.
- Overlay settings do not affect AI labels.
- Linear X steering from the current PiSD patches is preserved.
- `turn_gain`, motor `turn_curve`, and Manual Drive `steer_strength` remain removed from real steering.
- Recording/snapshot folder structure is preserved.

## Verification performed

Static/simulation validation performed locally after applying the full patch chain from `PiSD_0_8_0` through `PiSD_0_8_11`:

```bash
python3 -m compileall -q pisd scripts PiSD.py
python3 scripts/test_recording_service.py
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Also verified that `overlay_settings.json` and `overlay_settings_history.jsonl` are included in both recording and snapshot folders created by the recording service test.

## Known limits / next steps

- Hardware camera/motor testing was not run in this container.
- Full Flask route testing was not run here because this container environment does not include Flask.
- piTrainer still needs to be updated separately to read and apply `overlay_settings.json` automatically.
