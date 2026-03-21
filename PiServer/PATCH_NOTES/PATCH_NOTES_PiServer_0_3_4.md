# PATCH NOTES — PiServer 0_3_4

Baseline: PiServer_0_3_0 stable line, continuing from 0_3_3.

## What changed
- changed the default **Manual** workspace layout to match the approved viewer-first layout:
  - narrow left utility column
  - **Status / Telemetry** at top-left
  - **E-Stop** below status
  - **Recording** below E-Stop
  - large central **Camera preview**
  - **Runtime tuning** on the upper right
  - large **Manual drive** panel on the lower right
- bumped the layout storage key so browsers load the new default layout instead of reusing the old saved one
- changed the steering overlay gauge so the coloured steering bar now grows **from the centre zero point** instead of filling from the far left
- split the steering overlay arc into left/right segments for clearer direction reading

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_3_4.md`

## Notes
- the new default layout applies automatically because the layout storage key changed to `PiServerLayout:v0_3_4:*`
- users can still drag panels and save their own layout after first load
