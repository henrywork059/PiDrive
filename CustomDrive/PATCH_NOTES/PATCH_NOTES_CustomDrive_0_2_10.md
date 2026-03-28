# CustomDrive 0_2_10 Patch Notes

## Request summary
Fix the broken arm-control buttons that were returning HTTP 400 from the GUI, and restore the current intended arm behavior:
- Up / Down are press-and-hold lift controls.
- Open / Close are press-and-hold gripper controls.
- Lift uses servos 0 and 1.
- Gripper uses servo 2 only.

## Cause / root cause
The restored Git baseline still had the older arm-control contract:
- lift used target-angle movement instead of continuous hold movement
- gripper used one-tap hold/release actions instead of press-and-hold motion
- the frontend and backend action names had drifted, which could produce 400 responses when the browser posted newer hold-action names to the older backend

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/config/manual_control.json`

## Exact behavior changed
- Added continuous press-and-hold lift motion on servos 0 and 1.
- `start_up` now moves lift at -10°/sec while held.
- `start_down` now moves lift at +10°/sec while held.
- Added continuous press-and-hold gripper motion on servo 2 only.
- `start_open` now moves servo 2 at -10°/sec while held.
- `start_close` now moves servo 2 at +10°/sec while held.
- Added dedicated `stop_lift` and `stop_grip` handling.
- Reapplies the current held angles on startup/reload and on stop so the servos stay engaged instead of appearing released.
- Bumped the GUI asset version to `0_2_10` so the browser is more likely to load the updated JavaScript.

## Verification actually performed
- Patched forward from the uploaded `CustomDrive_0_2_0.zip` stable baseline.
- Reviewed the recent 0_2_7, 0_2_8, and 0_2_9 patch notes to avoid rolling back the intended arm behavior.
- Ran `python -m compileall CustomDrive` on the patched tree.

## Known limits / next steps
- After applying this patch on the Pi, restart the GUI server and do a hard refresh in the browser so the new `app.js` is loaded.
- Final physical direction still depends on linkage orientation; if a direction ever feels reversed, the sign can be swapped in the arm service without changing the GUI contract.
