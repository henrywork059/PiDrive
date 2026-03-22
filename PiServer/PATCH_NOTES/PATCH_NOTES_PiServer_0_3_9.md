# PiServer 0_3_9 Patch Notes

## Summary
This patch polishes the PiServer UI presentation without changing the approved 0_3_x workflow.

## What changed
- softened panel/card outlines and reduced visual heaviness
- added a simple shared size system for titles, labels, values, notes, spacing, and padding
- shortened repeated labels across the main panels
- standardized internal panel structure with shared panel sections and footer sections
- improved responsive priority behavior:
  - low-priority details hide first on narrow panels
  - medium-priority details hide next on very narrow panels
  - helper notes/subtitles collapse before main controls
- kept one alignment/style logic across cards, controls, labels, and values
- refined color usage so active/safety states stand out more clearly
- bumped app/static version to `0_3_9`

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_9.md`

## Notes
- This patch is built on top of the current `0_3_x` line and keeps the approved layout direction.
- Existing saved layouts are preserved. A hard refresh is still recommended after copying the files over.
