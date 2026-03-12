# PATCH NOTES — PiServer 0_1_13

## Goal
Move repo update / restart into a dedicated **Update** tab and make that tab enter a backend maintenance mode so the car is paused safely before update actions run.

## What changed
- Added a new top-level **Update** tab in the web UI.
- Added backend `maintenance_mode` state to PiServer runtime status.
- Opening the `Update` tab now:
  - forces throttle to zero
  - stops motor output
  - stops recording
  - engages emergency stop automatically
  - blocks runtime drive/model/record/config actions
- Leaving the `Update` tab exits maintenance mode but keeps the system stopped until the user resumes manually.
- `Update from Repo` and `Restart Server` now require **Update tab / maintenance mode** instead of asking the user to engage E-stop manually first.
- The Update page focuses the layout on status, live viewer, and update/system controls.
- Added cache-busting query strings for `app.js` and `styles.css` via version `0_1_13`.

## Files changed
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_13.md`

## Validation checklist
1. Replace the patch files into your current `0_1_12` working copy.
2. Start PiServer from your Git-backed folder, for example:
   - `/home/pi/PiDrive/PiServer`
3. Open the browser UI and click the new **Update** tab.
4. Confirm:
   - the status banner says maintenance mode is active
   - recording stops automatically
   - update / restart buttons become usable
   - drive/model/record controls are disabled
5. Click **Check repo** and verify branch / commit / remote appear.
6. Click **Update from Repo** and verify it no longer asks you to manually E-stop first.
7. Leave the Update tab and confirm the system remains stopped until you clear E-stop and resume manually.

## Notes
- This patch does not redesign the docking system. It only adds the Update tab / maintenance behavior on top of the current desktop UI.
- The backend now enforces maintenance-mode blocking, so update safety is not dependent on the browser alone.
