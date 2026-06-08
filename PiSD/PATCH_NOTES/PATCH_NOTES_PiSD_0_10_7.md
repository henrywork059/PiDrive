# PiSD 0.10.7 Patch Notes

## Request summary

User requested two v10-forward UI/runtime updates:

1. Add the recording download panel to the AI Mode page.
2. Make the Space bar a STOP shortcut for all modes, panels, and PiSD pages.

This patch builds forward from `PiSD_0_10_0.zip` plus accepted patches `0_10_1` through `0_10_6`.

## Root cause / reason for change

- AI Mode could start/stop recordings and save snapshots, but the saved recording/snapshot library panel existed only on Manual Drive.
- Space had page-local meanings. In AI Correction it centred correction, in AI Manual pad it stopped manual mode, and on other pages it was not consistently wired as a STOP command.
- Keeping recording-folder management inside the large AI controller would make the AI page harder to maintain, so this patch adds a small reusable browser helper for the recording download panel.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/README.md`
- `PiSD/docs/AI_MODE_CODE_MAP.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/js/global_space_stop.js`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/recording_download_panel.js`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/templates/autopilot.html`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_7.md`

## Behaviour changed

### AI Mode recording panel

- Added a `Records & snaps` panel to `/ai-mode`.
- The panel can:
  - refresh saved recording and snapshot folders;
  - display selected-folder name, frame count, size, modified time, folder id, and zip name;
  - download the selected folder through `/api/recording/download.zip`;
  - delete a selected inactive folder through `/api/recording/delete`;
  - keep delete disabled for active/running recording folders.
- AI snapshot/record actions now refresh the AI recording panel after saving or toggling a session.

### Smaller browser scripts

- Added `pisd/web/static/js/recording_download_panel.js` for the recording-folder panel.
- Added `pisd/web/static/js/global_space_stop.js` for shared Space STOP behaviour.
- `ai_mode.js` still owns AI UI state, model actions, correction input, and Manual-pad takeover state.
- `manual_drive.js` now only listens to the shared stop event to clear local pad/keyboard readouts.

### Global Space STOP

- Space now triggers the shared STOP helper across PiSD templates.
- On `/ai-mode`, Space sends:
  - `/api/ai/stop`
  - `/api/control/stop`
- On other pages, Space sends:
  - `/api/control/stop`
- The helper dispatches `pisd:space-stop` so page scripts can clear local keyboard/pad UI state.
- The helper ignores text-entry/editing controls such as text/number/range inputs, selects, textareas, and content-editable elements.

### AI Mode shortcut labels

- AI Correction and AI Manual pad now label Space as `Space STOP` instead of correction-centre/manual-only stop.
- Existing `r` and `s` shortcuts are preserved:
  - `r` toggles recording;
  - `s` saves a snapshot.

## Preserved / anti-rollback checks

This patch preserves accepted behaviour from the previous v10 patch chain:

- `Start live` one-button workflow remains unchanged.
- AI Mode `Snapshot` and `Record` buttons remain in the camera panel.
- AI Mode `r` and `s` shortcuts remain available.
- Additive AI correction equation remains `AI + manual * Correction %`.
- Fixed-throttle mode still applies fixed throttle after correction.
- Full AI Manual pad takeover remains a direct `/api/control/manual` path.
- Shared AI safety/motor-output acknowledgement controls remain outside the three toggled panes.
- `Save AI settings` remains a single button outside the toggled panes.
- The `0_10_5` smaller backend helper split remains intact.

## Verification actually performed

Applied and tested on a clean extracted state built from:

```text
PiSD_0_10_0.zip
+ PiSD_0_10_1_patch.zip
+ PiSD_0_10_2_patch.zip
+ PiSD_0_10_3_patch.zip
+ PiSD_0_10_4_patch.zip
+ PiSD_0_10_5_patch.zip
+ PiSD_0_10_6_patch.zip
```

Commands run:

```bash
cd /mnt/data/pisd_work_0107/PiSD
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/global_space_stop.js
node --check pisd/web/static/js/recording_download_panel.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --status-only
```

Results:

- Compile and JavaScript syntax checks passed.
- AI Mode static/source/helper checks passed.
- Standard validation without API/camera/motor/GUI checks passed.
- Standard validation with static GUI/source checks passed.
- Status-only command returned `PISD-OK-000` in simulation mode.

## Not hardware-verified here

- Real Pi Chromium Space shortcut behaviour.
- Real AI Mode recording-panel refresh/download/delete in the browser.
- Real zip download from Pi storage.
- Real motor STOP response from Space on hardware.
- Real AI inference while using global Space STOP.
- Real camera stream and snapshot/record files on Pi hardware.

## Known limits / next steps

- Space STOP is intentionally ignored while focus is inside text-like/editing fields so users can still type and edit numeric settings safely.
- Browser download behaviour still depends on the user's browser accepting `window.location.assign(...)` for the zip endpoint.
- The helper is written for the AI page's new `data-recording-download-panel="ai"` panel; Manual Drive still uses its existing local recording-list code and can be migrated to the shared helper in a later cleanup if desired.
