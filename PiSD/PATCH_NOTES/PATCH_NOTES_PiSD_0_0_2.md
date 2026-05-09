# PATCH NOTES - PiSD_0_0_2

## Request summary

Add testing scripts for the PiSD camera service, motor service, and API calls so the hardware/service wiring can be checked directly while continuing to use PiSD as a clean `PiDrive/PiSD` development path.

## Cause / reason

`PiSD_0_0_1` added real camera and motor service boundaries, but testing was still mostly described in documentation. The project needed runnable scripts that can verify:

- service imports and default config loading
- camera start/frame/JPEG behavior
- motor steering/throttle mapping
- STOP behavior
- Flask API route calls
- live HTTP route calls against a running server

The scripts also need to be safe by default so motor output does not start accidentally during development.

## Files added

- `PiSD/scripts/check_service_imports.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/scripts/test_camera_service.py`
- `PiSD/scripts/test_live_http_api.py`
- `PiSD/scripts/test_motor_service.py`
- `PiSD/test_outputs/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_2.md`

## Files changed

- `PiSD/README.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/pisd/__init__.py`

## Exact behavior changed

### Service test scripts

Added `PiSD/scripts/` with direct service checks:

- `check_service_imports.py`
  - imports PiSD services
  - loads `config/defaults.json`
  - creates the Flask app factory
  - reports optional dependency availability

- `test_camera_service.py`
  - starts the camera service
  - waits for frame sequence growth
  - saves a JPEG frame to `test_outputs/camera_service_frame.jpg`
  - supports `--hardware` for Picamera2 testing on Raspberry Pi

- `test_motor_service.py`
  - checks motor mapping in simulation mode by default
  - applies low-power forward, steering, reverse, and stop commands
  - supports pin overrides
  - requires both `--hardware` and `--enable-motor-output` before real GPIO PWM output is sent

- `test_api_endpoints.py`
  - uses Flask's test client to call service endpoints without starting a network server
  - verifies camera frame JPEG bytes
  - verifies manual control returns left/right outputs
  - verifies stop resets motor outputs

- `test_live_http_api.py`
  - calls a running PiSD server through HTTP using `requests`
  - verifies status, camera start, frame JPEG, motor config, and stop endpoints
  - skips movement command unless `--enable-motor-output` is used

### Documentation

Updated README and test docs with the exact commands for running the new checks.

Updated directory instructions to define:

- `PiSD/scripts/` for runnable checks
- `PiSD/test_outputs/` for small generated diagnostic files

### Version marker

Updated package version from `0.0.1` to `0.0.2` in:

- `PiSD/pisd/__init__.py`

## Verification actually performed

Performed locally in simulation mode:

```bash
python3 -m py_compile PiSD.py pisd/app.py pisd/core/value_utils.py pisd/services/camera_service.py pisd/services/motor_service.py scripts/*.py
python3 PiSD.py --status-only
python3 scripts/check_service_imports.py
python3 scripts/test_camera_service.py --seconds 1 --min-frames 1
python3 scripts/test_motor_service.py --duration 0.01
```

Also ran:

```bash
python3 scripts/test_api_endpoints.py
```

The API script itself started correctly but exited with the expected dependency message because Flask is not installed in this local packaging environment. It should be run after `python -m pip install -r requirements.txt`.

Package structure was checked after zipping to confirm the archive starts at `PiSD/` and does not include unrelated PiDrive folders.

## Not verified here

Real Raspberry Pi hardware was not tested in this environment because no physical Raspberry Pi camera or motor driver is attached. Flask-backed API execution was also not fully verified here because Flask is not installed in this container.

The following commands are prepared for hardware-side verification on the Pi:

```bash
python scripts/test_camera_service.py --hardware
python scripts/test_motor_service.py --hardware --enable-motor-output
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

## Known limits / next steps

- No persistent runtime settings store yet.
- No snapshot folder manager yet.
- No model/autonomy service yet.
- The current GUI remains a simple service sandbox shell.
- Next useful step is to add a minimal GUI test page for camera controls, motor calibration, and service logs once hardware behavior is confirmed.
