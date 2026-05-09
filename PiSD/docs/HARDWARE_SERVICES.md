# PiSD Hardware Service Notes

## Why PiSD has service tests

PiSD is intended to develop and test PiServer-style GUI and runtime functions from a clean path. The camera and motor services must therefore be testable without depending only on the browser UI.

The `scripts/` folder now contains service-level and API-level checks so the hardware path can be verified step by step.

## Reference approach

PiSD refers to the existing `PiServer/piserver/services/camera_service.py` and `PiServer/piserver/services/motor_service.py` patterns:

- optional Raspberry Pi imports
- simulation fallback on non-Pi machines
- safe clamping of motor values
- explicit camera start/stop behavior
- JSON status from APIs

PiSD does not overwrite or import PiServer code directly.

## Camera service

Path:

```text
PiSD/pisd/services/camera_service.py
```

Responsibilities:

- start/stop camera capture
- use Picamera2 when hardware mode is enabled and available
- generate simulated frames otherwise
- encode frames as JPEG for browser preview
- expose camera config and status
- avoid stale repeated snapshot/preview state by updating frame sequence

Important endpoints:

```text
POST /api/camera/start
POST /api/camera/stop
GET  /api/camera/config
POST /api/camera/apply
GET  /api/camera/frame.jpg
GET  /video_feed
```

Service test:

```bash
python scripts/test_camera_service.py
python scripts/test_camera_service.py --hardware
```

Expected output:

- `start_ok=True`
- frame sequence increases
- latest JPEG is saved to `test_outputs/camera_service_frame.jpg`
- hardware mode uses `backend: picamera2` when the real camera opens

## Motor service

Path:

```text
PiSD/pisd/services/motor_service.py
```

Responsibilities:

- map steering/throttle to left/right motor outputs
- apply direction, max speed, bias, and steer mix
- use RPi.GPIO-style PWM when hardware mode is enabled and available
- run in simulation mode otherwise
- always stop outputs on `/api/control/stop`

Default BCM pins:

```text
Left motor:  GPIO 17, GPIO 27
Right motor: GPIO 22, GPIO 23
PWM:         1000 Hz
```

These match the current PiServer-style defaults and can be changed through `config/defaults.json` or `/api/motor/apply`.

Service test:

```bash
python scripts/test_motor_service.py
```

Real GPIO output test:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

The real output flag is separate from `--hardware` so a user can inspect the hardware path without accidentally moving the motors.

## API call testing

Local Flask test-client check:

```bash
python scripts/test_api_endpoints.py
```

Live HTTP check against a running server:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

The live HTTP script checks the same routes over the real server socket. It skips the manual motor movement call unless `--enable-motor-output` is added.

## Hardware safety

Real hardware is not enabled by default.

Use the server hardware flag:

```bash
python PiSD.py --hardware
```

Use the motor test output flag only when safe:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

Without these flags, motor commands only update simulated left/right values and print `[PiSD MOTOR SIM]` logs.

## Known limits

- No persistent runtime settings store yet.
- No snapshot folder manager yet.
- No model/autonomy service yet.
- The web UI is still a small test shell, not the final PiServer replacement UI.

## Error reporting expectations

Hardware service failures must be visible through both service status and API responses.

Camera examples:

- missing Picamera2 reports `PISD-CAM-001`
- Picamera2 open failure reports `PISD-CAM-002`
- capture failure reports `PISD-CAM-004`
- JPEG encode failure reports `PISD-CAM-005`
- no frame available reports `PISD-CAM-006`

Motor examples:

- missing GPIO reports `PISD-MOT-001`
- GPIO/PWM setup failure reports `PISD-MOT-002`
- motor output failure reports `PISD-MOT-003`
- stop failure reports `PISD-MOT-004`

Check the shared registry here:

```text
PiSD/pisd/core/errors.py
PiSD/docs/ERROR_CODES.md
```

Check reporting schema without hardware:

```bash
python scripts/check_error_reporting.py
```
