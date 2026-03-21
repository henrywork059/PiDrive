# PiServer 0_2_19 Patch Notes

## Base
Built from the 0_2_17 UI layout (the last good UI direction), then updated without reintroducing the older mixed-panel layout from 0_2_18.

## Fixes in this patch
- keeps the 0_2_17 status/telemetry panel, separate E-Stop panel, and no System + config panel
- removes the on-screen arrow pad from Manual drive while keeping smooth keyboard control and joystick drag
- changes Recording into a large toggle-style control similar to the E-Stop presentation
- adds Steering bias to Runtime tuning
- includes Steering bias in runtime control updates, saved runtime config, runtime reload, and live status
- shows Steering bias in the Status / Telemetry panel
- improves recording toggle responsiveness by updating its UI state immediately while the request is in flight
- bumps app/static version to 0_2_19 so the browser reloads the corrected frontend

## Files changed
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/app.js
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/core/runtime_state.py
- PiServer/piserver/services/control_service.py
- PiServer/piserver/app.py
- PiServer/tests/test_control_service.py

## Notes
This patch is intended to replace the bad 0_2_18 UI state by overwriting the files above.
