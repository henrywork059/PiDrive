# CustomDrive 0_1_17 Patch Notes

## Request summary
- Do not add unrequested behavior.
- Remove WASD keyboard driving from the GUI.
- Remove the Forward / Backward / Left / Right drive buttons from the GUI.

## Cause / root cause
The previous GUI patch included extra manual-drive input methods beyond the requested drag pad. That added keyboard and directional button control paths the user did not ask for.

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_17.md`

## Exact behavior changed
- Removed the Forward / Left / Right / Reverse button group from the Manual Drive panel.
- Removed the WASD / arrow-key hint text from the Manual Drive panel.
- Removed keyboard driving handlers from the GUI JavaScript.
- Kept the drag pad and release-to-stop behavior unchanged.
- Kept the real PiServer motor control POST path unchanged.

## Verification performed
- Reviewed the current GUI template and JavaScript from the latest generated CustomDrive GUI patch.
- Checked that button IDs removed from the HTML are also no longer referenced by the GUI JavaScript.
- Confirmed the remaining drag-pad control path still posts through `/api/control`.

## Known limits / next steps
- This patch does not change the drag-pad logic, camera, arm controls, or settings windows.
- If needed later, keyboard drive can be restored behind an explicit setting instead of being always enabled.
