# PATCH_NOTES_PiServer_0_1_20

## Summary
Small patch for Camera settings persistence.

## Changes
- `Apply + Restart camera` now also saves the current camera settings into `config/runtime.json`.
- Removed the `Reload camera settings` button from the Camera panel.
- Updated the Camera panel messaging to make it clearer that saved settings are loaded.
- Bumped the web app version to `0_1_20` so the browser reloads the updated page files.

## Why
The Camera format and other settings could be changed live but not persist unless the user separately saved the whole config. This made it look like camera settings were not sticking between restarts.

## Validation
1. Open the Camera tab.
2. Change camera settings such as format or resolution.
3. Click `Apply + Restart camera`.
4. Confirm the preview restarts.
5. Restart PiServer.
6. Confirm the camera settings remain applied after restart.

## Notes
- This patch does not change the core capture pipeline.
- If colors still look wrong after this patch, set Camera format back to `BGR888`, click `Apply + Restart camera`, and verify after restarting PiServer.
