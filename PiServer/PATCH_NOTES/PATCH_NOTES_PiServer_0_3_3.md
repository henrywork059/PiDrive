# PATCH NOTES — PiServer_0_3_3

## Summary
This patch builds on the approved 0_3_0 → 0_3_2 UI line and adds the requested recording/overlay improvements without bringing older panels or controls back.

## Changes
- Made the Recording panel buttons truly half-and-half.
- Kept Snapshot as a real backend action and improved its UI feedback while saving.
- Replaced the placeholder overlay toggle with a 3-state cycle:
  - OFF
  - Overlay 1: live throttle bar + live steering semicircle on top of the camera frame
  - Overlay 2: placeholder
- Added responsive frame overlay elements to the live preview.
- Bumped app/static version to 0_3_3 so the browser refreshes the updated UI.
- Updated the saved layout key to `PiServerLayout:v0_3_3:` so older local layouts do not distort the refreshed layout.

## Files changed
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/web/static/app.js
- PiServer/piserver/app.py

## Notes
- Overlay rendering is client-side and uses live status values already returned by PiServer.
- Snapshot still saves a real JPEG plus JSONL metadata through `/api/record/capture_once`.
