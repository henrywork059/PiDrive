# CustomDrive 0_2_6 Patch Notes

## Request summary
- Make the Open and Close buttons control only servo channel 2.
- Change Open and Close to press-and-hold behavior.
- Open should move servo 2 at +5 degrees per second while held.
- Close should move servo 2 at -5 degrees per second while held.

## Root cause
The current GUI still bound Open and Close as single-click actions, and the backend treated them as one-tap hold/release angle jumps. That meant gripper movement did not match the requested press-and-hold behavior, and it was easy to think nothing had changed.

## Files changed
- CustomDrive/custom_drive/arm_service.py
- CustomDrive/custom_drive/gui_web/static/app.js
- CustomDrive/custom_drive/gui_control_app.py
- CustomDrive/config/manual_control.json

## Exact behavior changed
- Open now starts continuous motion on servo channel 2 only.
- Close now starts continuous motion on servo channel 2 only.
- Releasing either button stops only gripper motion.
- Gripper motion rate defaults to 5.0 degrees per second using 1 degree steps.
- Lift motion on channels 0 and 1 is unchanged.

## Verification performed
- Reviewed the current 0_2_0 arm-service and GUI binding path.
- Confirmed the previous GUI bound Open and Close as click actions only.
- Updated the backend to provide dedicated start/stop gripper motion on channel 2.
- Updated the frontend to use hold-to-move bindings for Open and Close.
- Ran python -m compileall CustomDrive.

## Known limits / next steps
- Final physical direction still depends on the servo linkage; if Open and Close feel reversed physically, the action names can be swapped in a follow-up patch without changing the rate logic.
- This patch keeps gripper control on channel 2 and ignores older conflicting grip channel values in config.
