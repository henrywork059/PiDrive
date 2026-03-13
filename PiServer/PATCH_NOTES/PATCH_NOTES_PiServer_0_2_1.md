# PATCH NOTES — PiServer_0_2_1

## Goal
Complete the Manual tab so it can actually drive the car from the web UI, and add a separate Motor tab for left/right motor tuning.

## Main changes
- Manual tab now supports:
  - forward and reverse throttle from the joystick
  - centered neutral joystick
  - quick drive buttons for forward, reverse, left, and right
  - keyboard drive using `W/A/S/D` or arrow keys while the Manual tab is active
  - automatic switch to the `manual` algorithm when the Manual tab is opened
- Added new **Motor** top tab with a dedicated Motor Settings panel
- Motor settings now include:
  - left motor direction
  - right motor direction
  - left motor max speed
  - right motor max speed
  - left motor bias
  - right motor bias
- Applying motor settings now:
  - stops the motors for safety
  - updates the live motor service immediately
  - saves the settings into the runtime config
- Runtime config save/reload now includes motor settings
- Page layout now hides irrelevant panels per tab, so Camera and Motor get their own cleaner workspaces

## Files changed
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/README.md`

## Validation performed
- Python syntax compile passed for updated backend files
- JavaScript syntax check passed for updated frontend file

## What to test on the Pi
1. Open **Manual** tab and confirm the joystick now has a neutral center.
2. Push joystick upward and confirm forward drive.
3. Pull joystick downward and confirm reverse drive.
4. Test `W/A/S/D` or arrow keys on the Manual tab.
5. Open **Motor** tab and reverse one motor direction if needed.
6. Adjust left/right motor bias until the car tracks straighter.
7. Click **Apply motor settings** and confirm the settings remain after **Save config** / restart.

## Notes
- If the car drives the wrong way on one side, use the new Motor tab instead of editing GPIO logic in code.
- Bias is applied as a trim to wheel command magnitude, so small values like `0.02` to `0.08` are a good place to start.
