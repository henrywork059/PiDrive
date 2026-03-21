# PATCH NOTES — PiServer 0_3_5

Baseline: PiServer_0_3_0 stable line, continuing from 0_3_4.

## Why this patch exists
This patch focuses on two areas that were still weak in daily use:

1. manual driving feel was still a bit abrupt and not very tunable
2. the recording workflow did not surface enough feedback about what was saved and where it went

The goal of this patch is to make manual control easier to tune without code changes, and to make snapshot/recording actions feel more trustworthy in the UI.

## What changed

### Manual drive feel
- added **Steer curve** tuning in the **Manual drive** panel
- added **Throttle curve** tuning in the **Manual drive** panel
- added **Steer rate** tuning in the **Manual drive** panel
- added **Throttle rate** tuning in the **Manual drive** panel
- changed joystick/pad input to use a curved response mapping so the centre area can be made less twitchy
- changed keyboard/manual stepping to work through the same target shaping path
- lowered the control loop step interval a bit for smoother visible response
- kept release-to-zero behaviour, but now the return follows the adjustable rate settings
- saved the manual feel settings in browser local storage so they survive page reloads

### Camera / recording workflow
- added a real **snapshot confirmation flash** over the preview when a snapshot is successfully saved
- added **Session** display to the **Recording** panel
- added **Save path** display to the **Recording** panel
- added **Elapsed** timer display to the **Recording** panel while recording is active
- added **Last save** display to the **Recording** panel so the user can see the latest saved item path
- extended recorder status so the frontend can show the active session path, snapshot path, and latest saved file information

### Versioning
- bumped PiServer app/static version to **0_3_5**

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/recorder_service.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_5.md`

## Verification
The following checks were run on the patch build:
- `python3 -m py_compile piserver/app.py piserver/services/control_service.py piserver/services/recorder_service.py piserver/core/runtime_state.py`
- `node --check piserver/web/static/app.js`
- `python3 -m unittest discover -s tests -q`

Result:
- Python compile passed
- JavaScript syntax check passed
- test suite passed

## Notes
- manual feel settings are stored in the browser using `PiServerManualFeel:v0_3_5`
- layout storage remains on the approved `0_3_4` layout key, so this patch does not force a layout reset
- record/session path display uses relative PiServer data paths so they are readable in the web UI
