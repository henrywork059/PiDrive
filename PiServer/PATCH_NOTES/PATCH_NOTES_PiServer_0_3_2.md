# PiServer 0_3_2 Patch Notes

Baseline: PiServer_0_3_0 with the approved 0_3_1 UI cleanup retained.

## Changes
- Recording panel now uses a full-height Record toggle sized like the E-Stop panel.
- Added a one-shot Snapshot button to the left of Record.
- Added an Overlay ON/OFF button card to the Status / Telemetry strip as a placeholder UI control.
- Reduced overall UI text sizing by about 20 percent.
- Tightened the docking grid by about 20 percent and updated default layouts to match.
- Improved drag-pad sizing so it fills the Manual panel more naturally.
- Added a backend route and recorder helper to save a single snapshot frame with JSONL metadata.
- Bumped app version to 0_3_2 so browsers fetch refreshed assets.

## Changed files
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/web/static/app.js
- PiServer/piserver/app.py
- PiServer/piserver/services/recorder_service.py
- PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_2.md
