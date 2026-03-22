# PiServer 0_3_8 Patch Notes

## Summary
This patch fixes the session export selection bug where choosing the shared `snapshots` folder could jump back to the current recording session during status polling. It also makes panel card layouts respond better to the current panel width so metric cards and info boxes reflow into a more readable number of columns as panels are resized.

## What changed
- Fixed **Session export** selection stability:
  - selecting the `snapshots` folder no longer gets overridden by `/api/status` updates
  - the active recording session is only auto-selected when there is no valid current selection
- Improved **responsive box layouts** across panels:
  - status metric cards keep auto-fitting by panel width
  - runtime tuning fields reflow more cleanly when the panel is narrow or wide
  - recording buttons can stack when the panel becomes too narrow
  - recording metadata cards now auto-fit to the current panel width
  - session export info cards now auto-fit to the current panel width
  - wide cards such as path / last save only expand full-width when the panel is wide enough
- Bumped app/static version to `0_3_8`

## Changed files
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_8.md`

## Validation
- `python3 -m py_compile piserver/app.py`
- `node --check piserver/web/static/app.js`
- `python3 -m unittest discover -s tests -q`

## Notes
- This patch is built on top of the current `0_3_x` line and keeps the approved UI direction from `0_3_0` onward.
- Because the app version changed, the browser should request the updated JS/CSS after a refresh.
