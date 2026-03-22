# PiServer 0_3_16 Patch Notes

## Summary
This patch corrects the incomplete 0_3_15 visual change. The previous patch did not flatten the UI strongly enough, so the interface still showed gradients, glow-like surfaces, large text, and wide spacing.

## Changes
- reduced overall text sizing much more noticeably
- reduced panel/workspace padding and gaps further
- removed gradient backgrounds from the main UI surfaces
- removed shadow, glow, blur, and lighting-style effects
- forced a flat background for the app shell, panels, headers, cards, and controls
- made select/dropdown controls use a dark background with light text
- kept the existing layout and behavior intact while changing presentation only
- bumped app version to 0_3_16 so browsers fetch the updated assets

## Files Changed
- PiServer/piserver/web/static/styles.css
- PiServer/piserver/web/static/theme.js
- PiServer/piserver/app.py

## Notes
Hard refresh the browser after restarting PiServer so the new CSS and theme script replace any cached versions.
