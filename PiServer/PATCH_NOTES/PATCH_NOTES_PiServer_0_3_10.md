# PiServer 0_3_10 Patch Notes

## Summary
This patch fixes the missing Manual drag pad introduced by the recent UI polish and improves responsive layout behavior in the Status and Manual panels.

## Changes
- restored a reliable visible size for the Manual drag pad by making the Manual shell flex correctly and giving the joystick area a responsive minimum height
- merged the split Status card groups into one responsive grid so all cards auto-flow by available panel width
- kept the four manual tuning bars on a single row
- prevented the four manual tuning bars from collapsing into one column in narrow container mode
- bumped the app/static version to `0_3_10` so browsers reload the updated layout

## Included files
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`

## Notes
- This patch is intended to apply on top of the approved `0_3_x` UI line.
- Hard refresh the browser once after restarting PiServer so the updated CSS and layout key are picked up.
