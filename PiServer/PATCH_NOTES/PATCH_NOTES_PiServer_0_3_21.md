# PiServer 0_3_21 Patch Notes

Base: rebuilt from the last good `0_3_19` UI state.

## Why this patch
`0_3_20` was built from the wrong base and rolled multiple UI and behavior changes back to older code.
This patch restores the `0_3_19` line and keeps only the intended drag pad sizing improvement.

## Fixes
- restored the `0_3_19` UI, overlay, and theme behavior
- restored the newer page layouts and panel set
- restored real Overlay 2 styling and the separate theme script
- restored the improved manual drive behavior from `0_3_19`
- changed the manual drag pad to use the available panel space more reliably while keeping a square shape
- bumped the layout storage key so old/bad saved layouts do not interfere

## Included files
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/theme.js`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_21.md`
