# PiServer 0_3_1 Patch Notes

Baseline: PiServer_0_3_0

## Summary
This patch is a small UI cleanup built on the approved 0_3_0 stable baseline. It removes leftover helper text and makes the manual drag pad size itself with the panel more naturally.

## Changes
- Removed the Recording helper text: `Records live control output with timestamped image names and JSONL metadata.`
- Removed the Runtime Tuning bottom helper text.
- Removed the Manual Drive bottom helper text.
- Made the manual drag pad fill the available manual panel area instead of relying on the older fixed minimum-height behavior.
- Bumped the web asset/app version to `0_3_1` so browsers refresh the updated UI.

## Files Changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_1.md`

## Notes
This is a patch-only update and keeps the current 0_3_0 UI structure.
