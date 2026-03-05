# PATCH_NOTES piCar_0_0_2 – FPS & UI polish + Stop button

## What changed

1. Improved FPS on Pi 4:
   - Camera now created as Camera(width=426, height=240, fps=30) in server.py.
   - JPEG encoding uses quality=70 in camera.py to reduce CPU and bandwidth.
   - Together this should give smoother streaming on a Raspberry Pi 4 (4GB).

2. Joystick dot really at the bottom:
   - CSS for #joystickDot changed to top: 100% with transform(-50%, -100%).
   - resetJoystick() also sets dot.top = "100%".
   - Visually the resting position now touches the bottom of the control box.

3. Manual control UI tweaks:
   - Speed slider is explicitly 100% width, clearer label and readout.
   - Overall panel styling updated:
     - Dark gradient background.
     - Rounded panels with soft borders and shadows.
     - Live viewer card with shadow.
     - Joystick box with subtle glow.

4. STOP button:
   - New red Stop button in the manual control panel.
   - Clicking Stop:
     - Sets steering = 0, throttle = 0.
     - Resets joystick dot to bottom-middle.
     - Resets slider to 0 and text to Speed: 0.00.
     - Sends /api/control with {steering: 0, throttle: 0, mode: "manual"} to fully stop the car.

## Future ideas

- Add reverse driving via joystick (downwards drag).
- Per-wheel trim/inversion in motor_controller.py.
- Real recording format compatible with PC training GUI.
- Responsive layout for phones.

## Version

- Previous patch: piCar_0_0_1
- This patch:     piCar_0_0_2