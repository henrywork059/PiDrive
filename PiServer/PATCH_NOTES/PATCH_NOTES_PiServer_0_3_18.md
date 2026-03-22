# PATCH_NOTES_PiServer_0_3_18

## Summary
Adds a real Overlay 2 path visualization on the camera frame.

## Changes
- Replaced the Overlay 2 placeholder with a live SVG overlay.
- Overlay 2 now plots two points:
  - Point 1 at the bottom-centre of the frame.
  - Point 2 driven by the current throttle and steering values.
- Draws a quarter-oval style arc from Point 1 to Point 2.
- No Overlay 2 path or points are shown when throttle is zero or negative.
- Updated the overlay toggle note to describe Overlay 2 as an arc path.
- Bumped the app/static version to `0_3_18`.

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_18.md`
