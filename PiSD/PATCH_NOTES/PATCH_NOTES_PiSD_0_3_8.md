# PiSD 0.3.8 Patch Notes

## Request summary

The user reported that manual speed/steering still could not reach `1.0`, and requested a review of button/API calls. They also requested recording management features so a user can select recording/snapshot folders, download them as zip files to a PC, and delete selected folders.

## Root cause / findings

- Earlier safety patches intentionally clamped manual drive speed, left motor max speed, and right motor max speed to `0.65`. That prevented full-range testing even when the user wanted `1.0` available.
- Manual Drive had capture/record buttons, but no browser UI or API routes to browse, download, or delete recorded folders.
- Recording files already had traceable folder/session structure, but the GUI could not manage those folders directly.

## Files changed

- `PiSD/config/defaults.json`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/services/recording_service.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/css/pisd_design_system.css`
- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_recording_service.py`
- `PiSD/docs/RECORDING_DATA.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_8.md`

## Behaviour changed

### Manual speed range

- Manual speed can now reach `1.0`.
- Manual steering strength can reach `1.0`.
- Motor `left_max_speed` and `right_max_speed` now default to `1.0` and are clamped to the range `0.0` to `1.0`.
- Motor channel tests can now test speeds up to `1.0`.
- Low-level motor driver output now permits the full normalized range from `-1.0` to `+1.0`.

### Recording and snapshot folder management

Added APIs:

- `GET /api/recording/items`
- `GET /api/recording/download.zip?kind=<recording|snapshot>&id=<folder-id>`
- `POST /api/recording/delete`

Manual Drive now includes a compact `Recordings & snapshots` panel where the user can:

- refresh available recording/snapshot folders
- switch between recording folders and snapshot folders
- select a folder
- download the selected folder as a zip
- delete the selected folder after confirmation

Folder policy:

- Continuous recordings still use one folder per recording session.
- Single manual captures still share the same daily snapshot folder under `recordings/single_captures/YYYY-MM-DD/`.

### Error codes added

- `PISD-REC-008` — recording/snapshot folder not found or invalid
- `PISD-REC-009` — recording/snapshot folder delete failed
- `PISD-REC-010` — recording/snapshot zip failed
- `PISD-TEST-024` — recording library validation failed

## Safety / compatibility notes

- Deleting the active recording session is refused. The user must stop recording first.
- Recording folder IDs are resolved only inside the PiSD `recordings/` directory to avoid unsafe path traversal.
- Zip downloads preserve the selected folder contents under a top-level `PiSD_<kind>_<id>/` folder inside the zip.
- Existing recording folders remain compatible.
- Existing runtime settings with older low max-speed values are accepted; users can now raise values up to `1.0`.

## Verification actually performed

- `python3 -m compileall -q .`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_recording_service.py`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_responsive_layout_contract.py --static-only`
- `python3 scripts/test_ui_presentation_consistency.py --static-only`
- `python3 scripts/test_panel_presentation_page.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`

## Not verified here

- Real Pi browser download/delete interaction.
- Real camera/motor operation after applying this patch on the Pi.
- Large recording zip performance with very large datasets.
