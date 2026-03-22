# PiServer 0_3_11 Patch Notes

## Summary
UI polish patch on top of the 0_3_x line. This patch removes redundant recording/path status cards and refreshes the visual palette to a more restrained, product-like dark theme.

## Changes
- Replaced the **Record** status card with **Last save** in the main Status strip.
- Removed the redundant **Path** card from the Recording panel.
- Kept **Session**, **Elapsed**, and **Last save** in the Recording panel.
- Added a shortened last-save label in the Status strip so long filenames do not dominate the card.
- Reworked the main color palette away from bright neon blues/greens toward a warmer charcoal / taupe / clay / sage palette.
- Updated panel, button, overlay, and preview accent colors to match the revised palette.
- Bumped app version to **0_3_11** so browsers reload the new static assets.

## Files
- PiServer/piserver/web/templates/index.html
- PiServer/piserver/web/static/app.js
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/app.py
- PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_11.md

## Notes
- This patch is intended to be applied on top of the existing 0_3_x UI line.
- No backend API changes were required.
