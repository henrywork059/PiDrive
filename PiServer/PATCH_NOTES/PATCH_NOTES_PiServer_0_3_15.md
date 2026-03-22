# PATCH_NOTES_PiServer_0_3_15

## Summary
Flat compact visual cleanup on top of the 0_3_14 style-system build.

## Changes
- Reduced global text scale by about 30% from the current 0_3_14 style.
- Reduced UI spacing and margins/gaps by about 40% across headers, panels, controls, and workspace padding.
- Removed gradients, glow, blur, and shadow styling to create a flatter dashboard presentation.
- Added a new `opsFlat` theme in `theme.js` and made it the default active style.
- Forced dropdown/select controls to use a dark background with light text.
- Kept the layout and panel logic intact; this is a style-only refinement.

## Changed files
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/app.py`

## Notes
- Hard refresh the browser after updating so the new CSS and theme script load.
