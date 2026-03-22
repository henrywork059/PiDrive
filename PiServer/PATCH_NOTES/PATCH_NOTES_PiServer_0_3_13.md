# PiServer 0_3_13 Patch Notes

## Summary
Visual refresh patch on top of the 0_3_12 UI line. This patch does not change the approved panel layout direction. It updates the palette and styling system so the interface feels calmer, less synthetic, and more consistent.

## Changes
- Reworked the dark theme into a warmer charcoal / stone / bronze / olive palette
- Softened borders and reduced the heavier high-contrast box feel
- Refined top bar, panel headers, and mini badges for a more designed presentation
- Improved card surfaces, spacing, and button styling
- Updated preview overlay colors to match the new visual language
- Refined drag pad styling so it fits the rest of the dashboard better
- Tweaked the brand subtitle to better match the cleaned-up interface
- Bumped app version to 0_3_13 so browsers reload the updated CSS

## Included Files
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/app.py
- PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_13.md

## Notes
- Built from the current 0_3_x UI line, not from the older broken branch
- Layout behavior and recent panel fixes are intended to remain unchanged
