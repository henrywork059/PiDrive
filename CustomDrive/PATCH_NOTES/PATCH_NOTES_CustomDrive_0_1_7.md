# PATCH NOTES — CustomDrive 0_1_7

## Goal
Tighten the CustomDrive manual-control page so it matches the current PiServer style more closely and is easier to use in competition:

- remove the competition session panel
- reduce top title-bar height
- make the status panel a slimmer full-width strip
- move manual drive to the right side
- add arm buttons: **Up / Down / Hold / Release**
- keep the backend structure close to PiServer service usage for easier maintenance

## What changed

### 1. Manual-control UI reshaped to match PiServer more closely
Updated the manual page layout to follow the PiServer look and flow more closely:

- slimmer top header
- full-width status strip at the top of the workspace
- camera viewer on the left
- manual-drive panel on the right
- system/debug panel on the lower-left

This removes the older competition-session editor panel from the page.

### 2. Added a dedicated arm service
Added a new file:

- `CustomDrive/custom_drive/arm_service.py`

This is a small service-style backend for arm actions, similar to how PiServer separates concerns into services.

Supported actions:

- `up`
- `down`
- `hold`
- `release`

It also exposes alias methods (`open`, `close`, `lift`, `lower`, etc.) so future autonomous logic can reuse it more easily.

### 3. Added PCA9685-backed arm output
The new arm service can drive a PCA9685 through `adafruit_servokit` when enabled in:

- `CustomDrive/config/manual_control.json`

Config keys added:

- `arm.enabled`
- `arm.backend`
- `arm.channels`
- `arm.i2c_address`
- `arm.frequency_hz`
- `arm.lift_channel`
- `arm.grip_channel`
- `arm.lift_up_angle`
- `arm.lift_down_angle`
- `arm.grip_hold_angle`
- `arm.grip_release_angle`

Meaning:

- `lift_channel` handles **Up / Down**
- `grip_channel` handles **Hold / Release**

### 4. Manual-control app backend cleaned up
Updated:

- `CustomDrive/custom_drive/manual_control_app.py`

Changes:

- keeps PiServer services for camera/motor/control/recording/model
- adds `arm` into `app.config["services"]`
- adds `/api/arm/action`
- adds `/api/arm/status`
- includes `arm_status` in `/api/status`
- reloads arm configuration whenever manual config is reloaded or saved

### 5. Manual-control config expanded and normalized
Updated:

- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/config/manual_control.json`

Changes:

- default manual-control port remains `5050`
- adds normalized arm config values
- keeps older competition keys for backward compatibility, but the UI no longer shows them

### 6. Frontend simplified and made easier to debug
Updated:

- `CustomDrive/custom_drive/manual_web/templates/index.html`
- `CustomDrive/custom_drive/manual_web/static/styles.css`
- `CustomDrive/custom_drive/manual_web/static/app.js`

Changes:

- removed the competition session panel from the UI
- added a full-width, lower-height status strip
- reduced top header height
- moved manual-drive panel to the right side
- added arm action buttons
- retained PiServer-style polled JPEG preview
- kept throttled control posting to avoid flooding the backend
- shows arm status and arm error messages in the page

### 7. Manual launcher kept on 5050
Updated:

- `CustomDrive/run_custom_drive_manual.py`

This keeps the manual-control app aligned with the rest of your CustomDrive web tools on port `5050` by default.

### 8. README updated
Updated:

- `CustomDrive/README.md`

Added notes for:

- the new manual layout
- arm control
- PCA9685 configuration
- port `5050`

## What to configure on the Pi
Edit:

- `CustomDrive/config/manual_control.json`

Example:

```json
"arm": {
  "enabled": true,
  "backend": "pca9685",
  "channels": 16,
  "i2c_address": 64,
  "frequency_hz": 50,
  "lift_channel": 0,
  "grip_channel": 1,
  "lift_up_angle": 40,
  "lift_down_angle": 115,
  "grip_hold_angle": 70,
  "grip_release_angle": 130
}
```

## Dependency note
For real PCA9685 output on the Pi, you still need the Adafruit ServoKit dependency installed in the Pi environment.
Typical package:

```bash
python -m pip install adafruit-circuitpython-servokit
```

## Verification completed
- `python -m compileall CustomDrive`

## Not fully verified in this container
- Real PCA9685 hardware output, because the container does not have your Pi I2C hardware stack.
