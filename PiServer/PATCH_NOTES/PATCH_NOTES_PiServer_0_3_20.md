# PiServer 0_3_20 Patch Notes

## Summary
This patch makes the manual drag pad use as much space as possible while keeping a square shape.

## Problem
The manual drag pad stayed noticeably smaller than the available space inside the Manual panel, especially after resizing the panel.

## Changes
- Added a dedicated `joystick-stage` wrapper in the Manual panel.
- Converted the Manual panel body into a vertical flex layout so the joystick stage can take the remaining free space.
- Added responsive sizing logic in `app.js` to compute the largest square that fits inside the Manual panel after accounting for the other controls.
- Added resize handling for panel resizing, window resizing, and tab switching.
- Bumped the asset version to `0_3_20` so the browser reloads the updated files.

## Files Changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/app.py`

## Verification
- Resize the Manual panel larger and smaller.
- Confirm the drag pad expands to the maximum square that fits the panel.
- Switch away from the Manual tab and back again.
- Confirm the pad recalculates correctly.
