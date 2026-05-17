# PiSD 0.3.6 Patch Notes — Recording Folder Policy, Speed Clamp Hardening, and Palette/UI Indicators

## Request summary

The user reported that the Manual Drive/Settings UI still showed max speed and left/right max speed as `1`, wanted a clearer recording indicator, wanted a visible notice when a single frame is captured, requested another review of style/layout, asked for a defined colour palette, and clarified recording storage rules:

- each continuous recording must be in its own folder
- all single captured frames should be saved to the same folder

## Cause/root cause

- Motor output limits were clamped inside `MotorService`, but older `config/runtime_settings.json` files could still keep `left_max_speed` and `right_max_speed` as `1.0`, causing the Settings page to display unsafe stale values.
- The recording service previously treated every single capture like a standalone mini-session, creating a separate snapshot folder for each frame.
- Manual Drive had record/capture buttons, but the recording state and capture completion feedback were not visible enough for normal use.
- Colour usage was spread across CSS variables without a clear documented palette.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/core/presentation_registry.py`
- `PiSD/pisd/services/recording_service.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/css/pisd_design_system.css`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_recording_service.py`
- `PiSD/scripts/test_ui_presentation_consistency.py`
- `PiSD/docs/COLOR_PALETTE.md`
- `PiSD/docs/PRESENTATION_DEVELOPMENT.md`
- `PiSD/docs/RECORDING_DATA.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_6.md`

## Behaviour changed

### Speed/settings hardening

- Backend settings normalisation now clamps persisted motor values:
  - `left_max_speed <= 0.65`
  - `right_max_speed <= 0.65`
  - `steer_mix <= 1.0`
  - motor bias in `[-0.35, 0.35]`
- Settings-page JavaScript also normalises values before display/save so stale browser/local/runtime values do not reintroduce `1.0` max speed.

### Manual Drive recording feedback

- Added a visible `REC off` / `REC on` indicator in the Manual Drive camera panel.
- Added a capture notice line under the camera controls.
- Pressing `Capture frame` now gives a visible user-facing message showing the frame ID/path summary.
- Starting/stopping recording also updates the visible notice.

### Recording folder policy

- Continuous recording still creates one folder per recording session:

```text
PiSD/recordings/YYYY-MM-DD/YYYYMMDD_HHMMSS_<label>_<id>/
```

- Single manual captures now share one same-day folder:

```text
PiSD/recordings/single_captures/YYYY-MM-DD/
```

- Single-capture `frame_index` now increments inside that daily folder.
- `records.jsonl` and `manifest.json` are kept in the shared single-capture folder.

### Colour palette

- Added `docs/COLOR_PALETTE.md`.
- Added `COLOR_PALETTE` to `pisd/core/presentation_registry.py`.
- Added semantic CSS palette variables in `pisd_design_system.css`.

### Layout/style

- Manual Drive layout remains semantic and locked:

```text
status drive
preview drive
preview stop
log log
```

- Status and Camera Preview stay stacked in the main column; Manual Control stays in the control column.

## Verification actually performed

Local verification performed in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_recording_service.py
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

## Not verified here

- Real Pi browser rendering
- Real OV5647 capture through the new Manual Drive capture notice
- Real recording on the Pi filesystem
- Real motor movement

These should be verified on the Raspberry Pi after applying the patch.
