# CustomDrive 0_2_13 Patch Notes

## Request summary
Fix the AI Settings window so uploaded models do not disappear when reopening the modal, and make the AI overlay use the same working preview frame path as the non-overlay preview.

## Root cause
1. The browser AI modal logic refreshed the model list from `/api/ai/models`, then immediately overwrote that list with the lighter `/api/status` payload, which intentionally did not include the model list. That made the select box appear empty on reopen.
2. The overlay preview path was reading a separate raw frame source (`get_latest_frame`) instead of annotating the same JPEG frame path that the working non-overlay preview already used. If the raw frame path lagged or was unavailable, the overlay route could fall back badly even though the normal preview JPEG path was fine.

## Files changed
- `CustomDrive/custom_drive/object_detection_service.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`

## Exact behavior changed
- Reopening **AI Settings** now keeps the uploaded model list visible.
- AI model selection no longer auto-saves `deployed_model` just from changing the dropdown; deploy remains an explicit action.
- The overlay preview now annotates the already-working JPEG preview frame instead of depending on a separate raw frame fetch.
- Deploy refresh order was tightened so the UI refreshes the model list first, then refreshes the preview and status.

## Verification performed
- Rebuilt latest working tree forward from `CustomDrive_0_2_0` plus accepted `0_2_10`, `0_2_11`, and `0_2_12` patch state.
- Ran `python -m compileall CustomDrive`.
- Checked the JS flow to confirm model-list state is no longer wiped by the status payload.
- Checked the camera-frame route to confirm overlay now uses the same JPEG preview source as the non-overlay path.

## Known limits / next steps
- This patch improves the overlay preview path, but if native Picamera2/libcamera/TFLite code still segfaults under long runtimes, that will need a separate stability patch focused on the Pi native stack.
