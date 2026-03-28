# CustomDrive 0_2_7 Patch Notes

## Request summary
- Make **Up** and **Down** true press-and-hold arm controls.
- Change gripper motion so:
  - **Open** moves servo 2 at **-10°/sec** while held.
  - **Close** moves servo 2 at **+10°/sec** while held.

## Cause / root cause
- The current GUI already used hold bindings for Up/Down, but both buttons were stopping through the generic `stop` action, which also stops gripper motion.
- The gripper direction was still set the opposite way from the requested behavior.
- The default gripper speed was still `5.0 deg/s`.

## Files changed
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/config/manual_control.json`

## Exact behavior changed
- Added dedicated `stop_lift` handling so the Up/Down hold buttons stop lift motion only.
- Kept Up/Down as press-and-hold controls in the GUI, now using `stop_lift` on release.
- Reversed gripper hold motion mapping:
  - `start_open` => servo 2 moves in the negative direction.
  - `start_close` => servo 2 moves in the positive direction.
- Increased gripper default motion speed from `5.0` to `10.0 deg/s`.

## Verification performed
- Applied the patch on top of `CustomDrive_0_2_0` plus accepted `0_2_1` to `0_2_6` forward patches.
- Ran `python3 -m compileall CustomDrive` on the patched tree.

## Known limits / next steps
- Actual final gripper direction still depends on physical linkage orientation. If it feels reversed on hardware, swap the sign direction in `start_grip_motion()` or rotate the horn position.
- Browser hard refresh may be needed so the updated `app.js` is loaded.
