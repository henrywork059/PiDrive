# PiSD 0.4.10 Patch Notes — Recording / Snapshot File Management Safety

## Request summary
- Add the next practical data-management patch for Manual Drive.
- Improve recording and snapshot folder selection, download, and deletion from the web UI.
- Keep the previous Manual Drive overlay, preview reliability, and fail-safe motor-stop work from 0.4.1 through 0.4.9.

## Cause / root cause
- PiSD already had basic recording/snapshot folder list, zip, and delete support, but the Manual Drive file panel gave little detail about exactly what folder was selected.
- The UI did not disable unsafe actions clearly when no folder was selected or when a folder represented an active recording.
- Backend path validation prevented most traversal attempts, but a special relative id such as `.` could resolve to the recordings root. That created avoidable risk for download/delete helpers that must only operate on selected child folders.
- Recording and snapshot kind mismatches could also be requested directly by API, for example asking for `single_captures` as a recording item.

## Files changed
- `PiSD/pisd/__init__.py`
  - Bumped runtime version from `0.4.9` to `0.4.10` for cache busting.
- `PiSD/pisd/app.py`
  - Adjusted recording delete API response status so active-session delete refusal returns conflict-style status instead of a generic not-found response.
- `PiSD/pisd/services/recording_service.py`
  - Hardened recording/snapshot folder id resolution.
  - Blocks root-level ids such as `.` / `./`.
  - Blocks resolved paths that equal the recordings root.
  - Blocks snapshot folders being requested through `kind=recording`.
  - Adds `download_name` and `can_delete` fields to collection summaries for clearer UI behaviour.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Added selected-folder summary fields in Manual Drive files panel.
  - Shows selected name, frame count, size, modified time, folder id, and zip name.
- `PiSD/pisd/web/static/css/manual_drive.css`
  - Added styling for the selected-folder summary panel.
  - Added disabled action-button presentation.
  - Added active/running state styling for selected recording folder summary.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Added selected-folder detail rendering.
  - Added human-readable file size and modified-time formatting.
  - Download button is disabled when there is no valid selection.
  - Delete button is disabled when there is no valid selection or when the selected folder is an active recording.
  - Delete confirmation now includes selected id, frame count, size, and modified time.
  - Download feedback now states the selected folder id and estimated size before browser download starts.
- `PiSD/scripts/test_recording_service.py`
  - Added checks that unsafe root-folder ids are rejected.
  - Added checks that snapshot folders cannot be requested through the recording kind.
- `PiSD/scripts/test_manual_drive_page.py`
  - Added static contract checks for the selected-folder summary UI and safe button-state logic.

## Exact behaviour changed
- Manual Drive → Files now clearly displays the selected recording/snapshot folder before download or delete.
- The user can see the selected folder id and expected zip filename before taking action.
- Delete is not offered for an active recording session.
- Backend delete/download helpers now reject ids that resolve to the recordings root.
- Backend delete/download helpers now reject snapshot-root requests under the wrong kind.
- Previous 0.4.x Manual Drive overlay, preview, STOP/fail-safe, and status-only refresh behaviour is preserved.

## Verification actually performed
- Applied the patch work on top of the cumulative 0.4.9 state built over clean `PiSD_0_4_0`.
- Ran `python3 -m compileall pisd scripts` — passed.
- Ran `node --check pisd/web/static/js/manual_drive.js` — passed.
- Ran `python3 scripts/test_recording_service.py` — passed, including new unsafe-id checks.
- Ran `python3 scripts/test_manual_drive_page.py --static-only` — passed.
- Ran `python3 scripts/test_main_dashboard.py --static-only` — passed.
- Ran `python3 scripts/test_front_page_tabs.py --static-only` — passed.
- Ran `python3 scripts/test_settings_persistence.py` — passed.
- Ran `python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor` — passed.

## Known limits / not verified
- Full Flask route checks were not completed in this container because Flask is not installed here.
- Hardware camera and motor behaviour were not tested in this container.
- Browser download behaviour was checked at code/static level only; final confirmation should be done on the Pi through the Manual Drive page.

## Apply command
From the PiDrive folder on the Pi:

```bash
cd ~/PiDrive
unzip -o PiSD_0_4_10_patch.zip
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard refresh the browser with `Ctrl + F5`.
