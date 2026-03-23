# PiServer 0_3_4 Patch Notes

## Problem
Some saved web-style settings were still not applying on the main PiServer page after reload or hard refresh, especially the global font size percentage.

## Root cause
Older `theme-ops-flat` CSS rules were still forcing `html.theme-ops-flat` to fixed font sizes like `68%` and `70%` with `!important`. Those rules overrode the saved `--font-scale` value loaded from the style settings. A few old compact-theme spacing and padding rules were also still hardcoded, so some spacing changes felt inconsistent.

## Changes made
- Bumped app version to `0_3_4` so updated static files are requested.
- Changed the style storage key to a stable key (`PiServerStyleCustom`) and added migration from older versioned keys, so saved styles survive future patches more reliably.
- Replaced the hardcoded `theme-ops-flat` html font-size overrides with `var(--font-scale, 82%) !important`.
- Updated several compact-theme spacing and padding overrides to use the saved CSS variables instead of fixed pixel values.
- Kept the settings model as one global font-size percentage and made that value drive the main PiServer page more directly.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/static/styles.css`

## Apply
Copy these patched files into your PiServer project, replacing the existing files.

## Verify
1. Restart the server with `python server.py`.
2. Open PiServer and press `Ctrl + Shift + R` once.
3. Open **Style settings** and change **Font size (%)**.
4. Save, go back to the main PiServer page, and refresh once.
5. Confirm the main page text size changes and stays changed after another reload.
