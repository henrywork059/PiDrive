# PATCH NOTES — PiServer_0_3_2

## Issue
The previous style-settings patch did not match the intended UX. The user expected a dedicated settings page opened by a button next to **Save layout**, but the earlier implementation was not visible in the running repo and did not open a separate page.

## Root cause
- The active PiServer repo still reported `APP_VERSION = 0_3_21`, so browser cache-busting kept using the older static bundle names.
- The requested interaction was a new page, while the earlier implementation was modal-oriented.
- Style customization needed to be applied consistently across both the main dashboard and the settings page.

## Changes made
1. Updated PiServer web app version to `0_3_2` for fresh static asset loading.
2. Added a new **Style settings** button beside **Save layout** on the main dashboard.
3. Added a new Flask route: `/settings`.
4. Added a dedicated `settings.html` page.
5. Added `settings.js` for live preview, save, and reset behavior.
6. Extended `theme.js` to support browser-saved custom style variables.
7. Added style variables for page margin, panel padding, control font size, and base font size.
8. Updated CSS so the custom style variables actually affect the interface.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/templates/settings.html`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/settings.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_2.md`

## Verification
- Confirmed the main toolbar now contains **Style settings** next to **Save layout**.
- Confirmed the button opens `/settings`.
- Confirmed preview updates live while moving sliders or changing colors.
- Confirmed **Save style** stores the style in local storage for this browser.
- Confirmed **Reset default** restores the default theme.
- Confirmed the changed static files are versioned with `0_3_2`.

## Notes
- Style settings are browser-local by design in this patch.
- This patch does not change drive logic, camera logic, or motor logic.
