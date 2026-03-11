# PATCH NOTES — PiServer 0_1_7

## Goal
Fix the web GUI issue where the user could not switch tabs and could not move panels reliably after updating to 0_1_6.

## Cause found
1. Tab switching waited for the backend response before updating the UI, so any backend hiccup made the tabs feel dead.
2. Dock dragging used only one interaction path and had a wide-screen cutoff, which reduced compatibility on some browsers and tablet-sized screens.
3. Static `app.js` / `styles.css` used the same URL, so a browser could keep an older cached file after patching.
4. There was an extra camera-control refresh call inside the calibration branch, which was unnecessary and could confuse the workspace refresh path.

## Changes made
- Mode/page tabs now switch in the browser immediately, then sync to the backend.
- If backend page sync fails, the UI rolls back and shows the error banner.
- Added broader docking compatibility handling and lowered the layout cutoff so docking remains available on more tablet/landscape screens.
- Added cache-busting query strings to static CSS and JS URLs in the HTML template.
- Removed the stray camera-refresh call from the calibration workspace render branch.
- Added README note explaining that panel dragging is done from the panel header.

## Files changed
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/README.md`

## Verification
- JavaScript syntax check passed with `node --check`.
- Python compile check passed with `python -m compileall`.

## Notes
- On very small phone screens, stacked mobile layout is still used for readability.
- Panel moving works by dragging the panel header area, not the whole panel body.
