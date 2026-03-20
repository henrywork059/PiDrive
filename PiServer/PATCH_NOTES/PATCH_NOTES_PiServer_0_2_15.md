# PiServer 0_2_15 Patch Notes

## Summary
This patch cleans up the PiServer panel structure and removes several duplicated or mixed controls from the web UI. It also moves the camera preview status line onto the frame so it no longer sits in the way of the preview area.

## Changes

### Camera preview
- Moved the preview status text (`Backend: ... · live preview`) onto the video frame as a bottom overlay.
- This keeps the preview information visible without taking extra space under the image.

### Manual drive panel
- Removed the long instructional paragraph that explained manual mode behavior.
- Removed the duplicate **Manual speed scale** slider.
- Removed the four quick-drive buttons: **Forward**, **Reverse**, **Left**, and **Right**.
- Kept joystick + keyboard driving.
- The **Max speed** slider in **Runtime tuning** now remains the single speed scaling control used for manual throttle scaling.

### Runtime tuning
- Removed the **Active algorithm / mode selection** control from the panel.
- Renamed **Max throttle** to **Max speed** for clearer behavior.

### Config panel
- Removed the **Config tools** panel from the layout and from all tabs.
- Layout save/reset toolbar buttons remain available in the top bar.

### Layout cleanup
- Updated default tab layouts so they no longer reserve space for the removed Config tools panel.
- Expanded adjacent panels where appropriate to use the freed space.

## Files changed
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_15.md`

## Verification
- `python3 -m py_compile piserver/app.py`
- `node --check piserver/web/static/app.js`
- Checked that all `getElementById(...)` targets still exist after removing UI elements.

## Notes
- This patch is patch-only and does not overwrite `config/runtime.json`.
- Hard refresh the browser after updating so the new `app.js` and `styles.css` are loaded.
