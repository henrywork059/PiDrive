# PiServer 0_3_19 Patch Notes

Base: PiServer_0_3_18

## Summary
This patch improves Overlay 2 presentation, makes the manual drag pad resize more intelligently with the panel, and shifts the control styling closer to the uploaded dark orange dashboard reference while keeping the current 0_3_x layout line intact.

## Changes
- Improved Overlay 2 rendering:
  - Replaced the rough single-path guide with a cleaner quarter-oval style cubic path
  - Added a subtle dark track under the accent path for better contrast on camera frames
  - Reduced point sizes and added cleaner ring styling so the plotted points read better
  - Kept Overlay 2 hidden whenever throttle <= 0
- Improved manual drag pad sizing:
  - Added dynamic pad sizing driven by panel size
  - The pad now tries to stay square and centered instead of stretching awkwardly
  - Added resize observation so panel dragging/resizing updates the pad shape live
- Updated theme styling toward the uploaded reference:
  - Shifted the accent from muted cyan to a restrained amber/orange
  - Tuned panel/control colors toward graphite + orange dashboard styling
  - Refined joystick and Overlay 2 styling to match the reference direction more closely

## Files Changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_19.md`

## Notes
- This patch is intended to apply on top of the approved 0_3_x line, especially `0_3_18`.
- A hard refresh is recommended after installing so the updated theme and overlay assets load cleanly.
