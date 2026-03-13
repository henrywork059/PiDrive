# PATCH NOTES — PiServer_0_2_6

## Patch type
Patch-only cumulative repair patch after stable baseline **PiServer_0_2_0**.

This patch is intended to replace the mixed partial files created by the earlier `0_2_1`–`0_2_5` attempts. It includes **all files modified after `0_2_0` that are needed for the Manual tab + Motor tab work** and also restores the startup/import chain to a consistent state.

## Main goals
1. Complete the **Manual** tab so it can actually drive the car.
2. Add a new **Motor** tab for direction, max speed, and bias tuning.
3. Avoid the import/startup bugs caused by partial patch chains.
4. Keep the already-good `0_2_0` camera path and startup structure intact where possible.

## What changed

### 1) Manual tab completed
- Manual control now supports a true **center-neutral joystick**.
- Joystick supports **forward and reverse**.
- Added keyboard controls:
  - `W / S` or `↑ / ↓` for forward and reverse
  - `A / D` or `← / →` for steering
- Added quick-drive buttons:
  - Forward
  - Reverse
  - Left
  - Right
  - Stop
- Entering the **Manual** tab automatically selects the `manual` algorithm.

### 2) Motor settings tab added
- Added a new top tab: **Motor**.
- Added live motor settings controls for:
  - left motor direction
  - right motor direction
  - left motor max speed
  - right motor max speed
  - left motor bias
  - right motor bias
- Applying motor settings:
  - updates the motor service immediately
  - stops the motors for safety
  - saves the settings through runtime config

### 3) Runtime state expanded
- Added motor tuning state fields:
  - `motor_left_direction`
  - `motor_right_direction`
  - `motor_left_max_speed`
  - `motor_right_max_speed`
  - `motor_left_bias`
  - `motor_right_bias`

### 4) Motor service fixed for real driving use
- Motor mapping now supports **negative throttle** for reverse.
- Added per-side tuning:
  - direction reversal
  - speed cap
  - bias trim
- Added config read/apply helpers so the UI and saved config can control motor tuning.

### 5) Control service updated
- Manual throttle now allows `-1.0 .. +1.0` instead of forward-only.
- Runtime config save/reload now includes motor settings.
- The status snapshot now reports motor tuning values back to the UI.

### 6) Startup/import chain restored to a consistent state
These files are included again in this cumulative patch so you can overwrite any mixed broken versions on the Pi:
- `PiServer/server.py`
- `PiServer/piserver/__init__.py`
- `PiServer/piserver/services/__init__.py`

This is specifically to avoid the earlier partial-state issues such as:
- `cannot import name 'create_app'`
- `cannot import name 'MotorService'`
- `cannot import name 'ControlService'`

## Files included in this patch
- `PiServer/server.py`
- `PiServer/piserver/__init__.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/__init__.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_6.md`

## Review / bug prevention notes
- Kept `server.py` and `piserver/__init__.py` aligned with the known-good `0_2_0` startup structure.
- Did **not** carry forward the earlier broken update/restart web patches.
- Kept camera service files out of this patch to reduce unrelated regression risk.
- Verified Python syntax by compiling the patched tree on top of the `0_2_0` baseline.

## Validation performed here
- Rebuilt a working tree by applying these files on top of `PiServer_0_2_0`.
- Ran Python compile checks on the rebuilt tree successfully.

## Not fully runnable in this environment
- Full Flask runtime test could not be completed here because `flask` is not installed in this container.
- GPIO / camera / motor hardware behavior still needs Pi-side validation.

## Recommended Pi test order
1. Copy this patch over your `PiServer_0_2_0`-based repo.
2. Run:
   ```bash
   cd ~/PiDrive/PiServer
   python3 server.py
   ```
3. Open the web UI.
4. Confirm:
   - Manual tab opens
   - Motor tab opens
   - joystick centers at neutral
   - forward and reverse both work
5. Open **Motor** tab and test:
   - reverse one motor if wiring direction is opposite
   - reduce one side max speed if needed
   - use bias to make the car track straighter

## Roll-forward guidance
If this patch works, treat it as the clean cumulative base after `0_2_0`, and continue future patches from there instead of stacking the broken partial `0_2_1`–`0_2_5` files.
