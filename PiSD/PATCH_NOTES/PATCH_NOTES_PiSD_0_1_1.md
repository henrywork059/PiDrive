# PATCH NOTES - PiSD 0.1.1

## Request summary

User requested the next PiSD patch to support car-specific motor configuration testing. Because motor wiring and direction can differ between cars, the motor test should test motors one by one, raw direction 1, raw direction 2, different speeds, stop, and related safety/error reporting.

## Cause / context

PiSD 0.1.0 had a working motor service and a general differential-drive test, but that test mixed steering/throttle into left/right outputs. It could confirm that GPIO output worked, but it was not ideal for identifying which physical motor, pin pair, or raw direction was correct on each individual car.

A safer calibration test needs to bypass steering mix and drive only one physical motor channel at a time.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/pisd/app.py`
- `PiSD/scripts/test_motor_channels.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/scripts/test_live_http_api.py`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/test_outputs/README.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_1_1.md`

## Behaviour changed

### Motor service

Added a motor-channel calibration method that can run:

- left motor only
- right motor only
- raw `direction_1`
- raw `direction_2`
- selected test speed
- selected duration
- automatic stop after every step

Raw direction naming is deliberate:

- `direction_1` means the first/forward pin in that motor pair is active.
- `direction_2` means the second/reverse pin in that motor pair is active.

This avoids assuming that raw direction 1 is always physically forward on every car.

### New script

Added:

```text
PiSD/scripts/test_motor_channels.py
```

Default run is simulation-only:

```bash
python3 scripts/test_motor_channels.py
```

Real hardware run requires explicit arming:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output
```

When real output is enabled, the script prompts before each step unless `--yes` is also supplied.

### New API endpoint

Added:

```text
POST /api/motor/test-channel
```

Example payload:

```json
{
  "side": "left",
  "direction": 1,
  "speed": 0.15,
  "duration": 0.35,
  "enable_motor_output": true
}
```

When the server is hardware-enabled, the endpoint refuses to move a motor unless `enable_motor_output` is true.

### Test output

The channel script writes:

```text
PiSD/test_outputs/motor_channels/summary.json
```

This is intended to help compare pin/direction observations between different cars.

## Error reporting

Added error codes:

- `PISD-MOT-007` — invalid motor channel test input.
- `PISD-MOT-008` — live API motor channel test was not armed with `enable_motor_output: true`.
- `PISD-MOT-009` — motor channel test output command failed.
- `PISD-TEST-007` — motor channel test script detected one or more failed steps.

All new responses include a PiSD code and structured JSON status.

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_motor_channels.py --speeds 0.05,0.1 --duration 0.05 --pause 0.0`
- `python3 scripts/test_motor_channels.py --speeds 0.05 --duration 0.05 --pause 0.0`
- `python3 scripts/test_motor_service.py`
- patch-only zip structure check
- confirmed only changed/new files are included in the patch zip
- confirmed `requirements.txt` remains the only dependency file and `requirement.txt` was not restored

## Not verified here

- Real Raspberry Pi motor movement, because this packaging environment has no GPIO/motor hardware.
- Flask API route execution in this packaging environment, because Flask is not installed here. The script and route code compile, and the Pi already confirmed Flask/live API operation in the previous stable baseline.
- Physical direction correctness, because that depends on observing each real car's wheel direction.

## Known limits / next steps

- This patch records what each side/direction/speed command did, but the user still needs to observe which direction is physically forward on each car.
- A future patch should add saved per-car motor profiles, so confirmed pin/direction/speed settings can be stored and selected from the GUI.
- A future GUI patch should expose this one-by-one motor channel test behind a safe calibration page.
