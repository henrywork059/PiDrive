# PiSD Test Plan

## Local checks

From inside `PiSD/`:

```bash
python -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py
python PiSD.py --status-only
python scripts/check_error_reporting.py
python scripts/check_service_imports.py
python scripts/test_api_endpoints.py
python scripts/test_camera_service.py
python scripts/test_motor_service.py
```

Expected in simulation mode:

- imports succeed
- error/reporting schema check succeeds
- default config loads
- Flask app factory creates the API app
- camera service starts and writes a JPEG under `test_outputs/`
- API test receives JPEG bytes from `/api/camera/frame.jpg`
- motor service maps steering/throttle into left/right outputs
- STOP resets left/right motor output to zero

## Package install check

```bash
python -m pip install -r requirements.txt
```

## Web smoke test

```bash
python PiSD.py
```

Open:

```text
http://127.0.0.1:5050
http://127.0.0.1:5050/api/status
```

Expected in simulation mode:

- web page loads
- status JSON returns and includes `code`, `last_error_code`, and `recent_errors` fields
- camera can start in simulation
- preview image changes over time
- steering/throttle sliders update motor simulation state
- STOP resets left/right motor output to zero

## API smoke test without network server

```bash
python scripts/test_api_endpoints.py
```

This uses Flask's local test client. It checks:

- `GET /api/status`
- `POST /api/camera/start`
- `GET /api/camera/frame.jpg`
- `GET /api/motor/config`
- `GET /api/errors`
- invalid JSON returns `PISD-API-001`
- `POST /api/control/manual`
- `POST /api/control/stop`
- `POST /api/camera/stop`

## Live HTTP API test

Start the server in one terminal:

```bash
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

In another terminal:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

This verifies the actual HTTP route path to the running server. It does not move motors unless this extra flag is used:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050 --enable-motor-output
```

## Raspberry Pi camera hardware test

Only run on the Pi with the camera connected and Picamera2 installed.

```bash
python scripts/test_camera_service.py --hardware
```

Expected:

- script prints `start_ok=True`
- status reports `backend: picamera2` if the real camera opened
- a JPEG is saved to `test_outputs/camera_service_frame.jpg`

If Picamera2 is unavailable or fails to open, the service should report the error and fall back to simulation rather than crashing.

## Raspberry Pi motor hardware test

Only run when the car is safe, wheels are lifted, and motor power is controlled.

Simulation-only mapping test:

```bash
python scripts/test_motor_service.py
```

Real GPIO output test:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

Optional pin override example:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output --left-pins 17,27 --right-pins 22,23
```

Expected:

- status reports `adapter: rpigpio` when GPIO is available and real output is enabled
- each low-power command runs briefly
- final stop command resets outputs to zero
- script calls `motor.close()` before exit

## Error-code reporting check

This test does not require Flask or Raspberry Pi hardware:

```bash
python scripts/check_error_reporting.py
```

Expected:

- returns `code: PISD-OK-000`
- verifies `ok_payload` and `report_payload`
- verifies camera and motor status include `last_error_code` and `recent_errors`

## Verification rule

Patch notes must only claim tests that were actually run.
