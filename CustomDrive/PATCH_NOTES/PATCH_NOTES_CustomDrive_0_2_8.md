# CustomDrive 0_2_8 Patch Notes

## Request summary
- Fix Up/Down so lift behaves as true press-and-hold motion.
- Make Up move servo channels 0 and 1 at -10°/sec while held.

## Cause / root cause
- The lift path was still implemented as movement toward preset target angles, which did not match the requested continuous hold behavior.
- The browser hold binding stopped on pointer leave, so slight finger or mouse drift could stop lift early and make it feel unreliable.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_control_app.py`

## Exact behavior changed
- Changed lift motion from target-based movement to continuous relative motion.
- `start_up` now moves lift servos 0 and 1 at -10°/sec while held, using the existing 1° step and 0.1s interval.
- `start_down` now moves lift servos 0 and 1 at +10°/sec while held.
- Lift motion now clamps at 0–180° and stops only lift motion on release.
- Improved hold-button handling with pointer capture so the button does not stop early when the pointer drifts outside the button while still held.
- Bumped the GUI app version so the browser is more likely to load the updated JavaScript immediately.

## Verification performed
- Applied the patch forward on top of `CustomDrive_0_2_0` plus the accepted arm-control patches through `0_2_7`.
- Ran `python3 -m compileall CustomDrive` on the patched tree.

## Known limits / next steps
- If the physical lift direction still feels reversed on the hardware linkage, swap the sign in `start_motion()` for `up` and `down`.
- Browser hard refresh may still be needed if an old cached script is retained.
