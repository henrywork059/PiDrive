# PATCH NOTES — PiServer_0_3_5

## Summary
This patch fixes the web style settings that still looked unchanged on the main PiServer page, especially under the `theme-ops-flat` compact overrides.

## User-reported problems
The following settings did not visibly update or only updated partly:
- Panel body padding
- Panel header padding
- Font size (%)
- Card spacing
- Field spacing

## Root cause
Older compact-theme CSS blocks still had many hardcoded `!important` values. Those rules overrode the newer style settings values loaded from `theme.js`, so changing settings in the modal did not fully affect the live PiServer page.

## Changes made
1. Bumped app/static version to `0_3_5` so the browser fetches the new CSS and JS.
2. Added dedicated style variables for:
   - `--font-scale-factor`
   - `--card-gap`
   - `--field-gap`
3. Added missing style-setting controls in the modal for:
   - Panel header padding
   - Card spacing
   - Field spacing
4. Renamed labels to match the intended behavior more clearly:
   - `Font size (%)`
   - `Panel body padding`
   - `Panel header padding`
5. Added end-of-file CSS binding rules that force the main PiServer page to use the saved variables even when `theme-ops-flat` legacy overrides are present.
6. Updated JS/theme handling so font scale also stores a numeric factor, allowing the compact UI text sizes to scale consistently instead of staying fixed.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_5.md`

## Verification notes
After applying the patch:
1. Restart the server.
2. Hard refresh the browser once.
3. Open **Style settings** and change the five reported controls.
4. Save and confirm the main PiServer page updates immediately and after reload.

## Notes
Style settings remain browser-local. Existing older saved style values are separated by the new storage key so stale cached values do not keep overriding the new behavior.
