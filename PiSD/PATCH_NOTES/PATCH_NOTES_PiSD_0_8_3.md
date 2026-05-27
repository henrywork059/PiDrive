# PATCH NOTES - PiSD_0_8_3

## Request summary

User reported that the live overlay's motor output display should show the car's intended motion values, not the hardware-signed PWM values after motor direction tuning. When the car is commanded to go forward, both left and right displayed output values should be positive even if one physical motor uses a saved `left_direction` or `right_direction` of `-1` to correct wiring.

This patch builds forward from `PiSD_0_8_0` plus accepted patches `PiSD_0_8_1_patch.zip` and `PiSD_0_8_2_patch.zip`.

## Cause / root cause

`MotorService.last_left` and `MotorService.last_right` represented the final values sent to the motor driver after applying motor direction multipliers. That is useful for hardware diagnostics, but it is not the clearest value for the live overlay or driver-facing readouts.

Example before this patch:

```text
throttle = +0.40
steering = 0.00
right_direction = -1

hardware output shown in overlay:
left  = +0.40
right = -0.40
```

The car may still move forward because the right motor wiring requires a negative PWM command, but the overlay readout looked like one side was reversing. This was confusing because the overlay should describe intended vehicle motion.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/services/recording_service.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/templates/motor_tuning.html`
- `PiSD/pisd/web/static/js/motor_tuning.js`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/SETTINGS_MANAGER.md`
- `PiSD/scripts/test_motor_steering_modes.py`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_3.md`

## Exact behaviour changed

### Intended output is now tracked separately

`MotorService` now tracks both output meanings:

```text
last_intended_left / last_intended_right
```

These are logical vehicle-motion values after speed/bias/max-speed tuning but before hardware direction multipliers.

```text
last_left / last_right
last_hardware_left / last_hardware_right
```

These remain the hardware-applied values after `left_direction` and `right_direction` are applied.

### Driver-facing live overlay uses intended output

Manual Drive live overlay and status strip now prefer:

```text
last_intended_left
last_intended_right
```

Therefore forward travel displays as:

```text
L +0.40 / R +0.40
```

even when the hardware values are:

```text
hardware L +0.40 / hardware R -0.40
```

This better matches what the car is intended to do.

### Motor Tuning readout uses intended output

The Motor Tuning page now labels the readout as `Intended motor output` and prefers the `left_intended` / `right_intended` values returned by timed tuning runs.

### API response compatibility preserved

Existing `left` and `right` values remain available as hardware-applied values for compatibility.

New fields are added where relevant:

```text
left_intended
right_intended
left_hardware
right_hardware
```

### AI display also uses intended output

AI Mode keeps hardware diagnostics internally but now reports/display `last_motor_output.left` and `last_motor_output.right` as intended vehicle-motion output. Hardware values are retained as:

```text
left_hardware
right_hardware
```

### Recording debug data is clearer

`records.jsonl` now stores trainer-facing motor outputs as intended values while also keeping hardware diagnostics:

```json
"motor_outputs": {
  "left": 0.40,
  "right": 0.40,
  "left_hardware": 0.40,
  "right_hardware": -0.40
}
```

`labels.jsonl` remains based on steering/throttle labels and is not changed.

## Preserved behaviour / rollback check

This patch does not roll back accepted `0_8_1` or `0_8_2` work:

- `turn_gain` remains removed from real motor steering.
- `turn_curve` remains removed from real motor steering.
- Steering X remains linear in `turn_rate` mode.
- Overlay tuning remains visual-only/manual and separate from motor tuning.
- Motor Tuning still has the live camera-backed overlay preview.
- Motor Tuning page styling remains aligned with the shared PiSD page/panel layout.
- `arcade_mix` fallback remains available.
- Existing hardware direction tuning still affects real motor output.

## Verification actually performed

Executed locally in simulation/static mode:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/main_dashboard.js
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Additional check added:

- `right_direction = -1` with forward throttle now produces hardware `right = -0.40` but intended `right = +0.40`, and the test passes.

## Verification not performed

- Real Raspberry Pi GPIO motor output was not tested here.
- Live browser camera/overlay rendering was not tested on actual Pi hardware.
- Full Flask route tests were not completed in this container because Flask is not installed in the environment.

## Known limits / next steps

- The full hardware values are available in API status for diagnostics, but the live overlay intentionally shows intended motion values only.
- If a future diagnostic page is added, it should show both rows explicitly: `Intended output` and `Hardware PWM output`.
