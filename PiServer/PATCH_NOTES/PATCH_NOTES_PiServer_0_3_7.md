# PATCH_NOTES_PiServer_0_3_7

## Summary
This patch improves the Training tab export workflow and model management by adding delete actions with confirmation support and by treating the shared snapshots folder like an exportable folder in the Session export panel.

## Changes
- Session export panel now lists the `snapshots` folder alongside recorded sessions.
- Snapshot folder can be downloaded as a ZIP from the Session export panel.
- Added a **Delete folder** button to the Session export panel.
- Added a **Delete model** button to the Model manager panel.
- Frontend now shows confirmation dialogs before deleting a session folder, the snapshots folder, or a model file.
- Backend now provides delete routes for session/snapshot folders and model files.
- Deleting the active loaded model clears the active model state safely.
- Added tests for session deletion, snapshot export, and model deletion.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/recorder_service.py`
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/tests/test_recorder_service.py`
- `PiServer/tests/test_model_service.py`

## Notes
- The snapshots folder is recreated automatically after deletion so future snapshot captures still work.
- Active recording sessions are protected from deletion until recording stops.
