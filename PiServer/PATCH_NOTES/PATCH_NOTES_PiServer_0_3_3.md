# PATCH NOTES — PiServer_0_3_3

## Summary
This patch updates the new web style editor so it works the way requested:
- the change applies to the main PiServer page
- the settings screen is a real scrollable page
- font size is now a single global percentage control
- more spacing controls were added
- the default panel layouts were adjusted across pages

## Cause of the issue
The previous attempt did not match the current repo baseline cleanly.
The repo still used the original PiServer web structure and did not actually contain the separate settings page files.
That meant the request needed a proper integration into the live PiServer web app instead of a partial overlay-style change.

## What changed

### 1) Real PiServer settings page
Added a dedicated `/settings` route and a scrollable `settings.html` page.
The PiServer top bar now has a **Style settings** button beside **Save layout**.
Clicking it opens the settings page.

### 2) Settings now apply to the main PiServer page
Added persistent style storage through shared theme logic in `theme.js`.
Saved values are stored in browser local storage and are automatically applied when the main PiServer page loads.
This means the settings page is now the editor, and the PiServer page is the live target.

### 3) Font size simplified
Removed the idea of multiple font-size controls.
There is now one global **Font size (%)** control that affects the whole UI.

### 4) More spacing controls
Added separate controls for:
- grid gap
- page padding
- panel body padding
- panel header padding
- control spacing
- section spacing
- card spacing
- field spacing
- corner radius

### 5) Default layout refresh
Updated the default panel boxes in `app.js` for:
- manual
- training
- auto
- camera
- motor

This gives a more balanced starting layout for the current PiServer page set.
Existing users with saved local layouts may still see their own saved layout until they press **Reset layout**.

### 6) Cache/version bump
Updated app version to `0_3_3` so static assets refresh more reliably.
Also updated the layout storage key version so the refreshed defaults can take effect for users who have not already saved a local layout.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/templates/settings.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/settings.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_3.md`

## Verification
Checked:
- Flask app syntax with `python -m py_compile piserver/app.py`
- `/settings` route exists
- Style settings button exists in `index.html`
- Shared theme loader is present
- New settings page files are present

## Notes
- Style settings are browser-local by design right now.
- If the main page still shows an older layout, press **Reset layout** once.
- If the browser still shows stale assets, do one hard refresh with `Ctrl + Shift + R`.
