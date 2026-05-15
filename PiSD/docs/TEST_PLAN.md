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

## Camera colour diagnostic test

Use this when the camera opens but the saved frame colour looks wrong.

```bash
python scripts/diagnose_camera_color.py --hardware
```

Optional extended check:

```bash
python scripts/diagnose_camera_color.py --hardware --include-rgb-format
```

Expected:

- files are saved under `test_outputs/camera_color/`
- `summary.json` records backend, capture source, colour path, metadata, and any PiSD error code
- `01_request_awb_auto.jpg` should be treated as the main preview baseline

Single-frame camera test with explicit preview path:

```bash
python scripts/test_camera_service.py --hardware --capture-source request
```

Raw array colour-order comparison:

```bash
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb --output test_outputs/array_rgb.jpg
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order bgr --output test_outputs/array_bgr.jpg
```

Manual AWB lock test:

```bash
python scripts/test_camera_service.py --hardware --awb-off --output test_outputs/awb_off_lock.jpg
```

Manual colour gains example:

```bash
python scripts/test_camera_service.py --hardware --colour-gains 1.5,1.2 --output test_outputs/manual_colour_gains.jpg
```

Only keep manual gains if the result is visually better under the real lighting used by the car.

---

## PiSD 0.0.5 camera settings tests

The visual camera path should use `capture_source=request`, with `01_request_awb_auto` confirmed correct. Raw array tests are optional; when needed, use `array_color_order=rgb` first because `91_array_rgb` was confirmed correct on the OV5647 setup.

### Dump camera capabilities

```bash
python3 scripts/dump_camera_capabilities.py --hardware
```

### Test individual camera settings

```bash
python3 scripts/test_camera_service.py --hardware --capture-source request
python3 scripts/test_camera_service.py --hardware --width 640 --height 360 --fps 15 --preview-quality 80 --buffer-count 4 --no-queue
python3 scripts/test_camera_service.py --hardware --manual-exposure --exposure-us 8000 --analogue-gain 1.5
python3 scripts/test_camera_service.py --hardware --awb-mode daylight
python3 scripts/test_camera_service.py --hardware --awb-off --colour-gains 1.8,1.2
python3 scripts/test_camera_service.py --hardware --brightness 0.05 --contrast 1.2 --saturation 1.2 --sharpness 1.1
```

### Run the camera settings matrix

```bash
python3 scripts/test_camera_settings_matrix.py --hardware
```

Optional raw array diagnostics:

```bash
python3 scripts/test_camera_settings_matrix.py --hardware --include-array-diagnostics
python3 scripts/diagnose_camera_color.py --hardware --include-array-diagnostics
```


---

## PiSD 0.1.1 one-by-one motor channel tests

Simulation-only check:

```bash
python3 scripts/test_motor_channels.py
```

Real GPIO check with wheels lifted:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output
```

Recommended low-speed first run:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --speeds 0.10,0.15,0.20 --duration 0.30
```

Expected:

- left motor is tested by itself
- right motor is tested by itself
- each side tests raw `direction_1` and `direction_2`
- each direction tests the requested speed list
- every step automatically stops
- summary file is written to `test_outputs/motor_channels/summary.json`
- final code is `PISD-OK-000` unless a step failed

Live HTTP API single-channel check with server already running:

```bash
python3 scripts/test_live_http_api.py --base-url http://127.0.0.1:5050 --enable-motor-output
```

This now also calls `POST /api/motor/test-channel` before the existing manual control check.
