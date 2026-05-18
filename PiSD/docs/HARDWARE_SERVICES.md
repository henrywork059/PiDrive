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

## Camera colour / AWB debugging notes

Patch `0.0.4` changed the default Picamera2 preview path from raw `capture_array()` plus OpenCV JPEG encoding to a Picamera2 request/PIL image path. This is intentional because the raw array path is useful for computer vision but can make colour debugging confusing when the array channel order is interpreted incorrectly.

Current camera colour-related settings in `config/defaults.json` after PiSD 0.5.6:

```json
{
  "capture_source": "request",
  "array_color_order": "rgb",
  "auto_white_balance": false,
  "awb_mode": "auto",
  "colour_gains_red": 0.0,
  "colour_gains_blue": 0.0,
  "awb_settle_seconds": 1.0
}
```

Recommended meaning:

- `capture_source: "request"` — use Picamera2 request image/JPEG path for preview; this is the preferred default for colour checking.
- `capture_source: "array"` — use raw array capture and PiSD/OpenCV encoding for computer-vision tests.
- `array_color_order` — only affects the `array` path. Use `rgb` by default; the `91_array_rgb` diagnostic was confirmed correct on the OV5647 setup.
- `auto_white_balance` — defaults to `false` for the tested OV5647 locked-AWB visual profile. Use `true` only when actively testing AWB-auto modes.
- `colour_gains_red` / `colour_gains_blue` — if both are above zero, PiSD sends Picamera2 `ColourGains`, which disables auto AWB.

Colour diagnostic command:

```bash
python scripts/diagnose_camera_color.py --hardware
```

This saves comparison frames under:

```text
PiSD/test_outputs/camera_color/
```

Compare these images first:

- `01_request_awb_auto.jpg` — older AWB-auto comparison; user testing showed it could still look too red/blue, so it is no longer the default.
- `02_request_awb_daylight.jpg` — daylight AWB comparison.
- `03_request_awb_off_lock.jpg` — lets AWB settle briefly, then locks it. This is now the PiSD default visual preview/training profile.
- `91_array_rgb_confirmed_correct.jpg` — confirmed correct raw array/CV path when `--include-array-diagnostics` is used.

Keep preview on `capture_source: "request"`; use `array_color_order: "rgb"` for CV/raw array processing.

If both request images are wrong, the issue is more likely camera tuning, lighting, AWB mode, or manual colour gains rather than OpenCV channel order.

---

## Camera controls expanded in PiSD 0.0.5

The camera service now exposes and reports these major categories:

- stream size, pixel format, FPS, buffer count, queue mode, JPEG quality
- hflip/vflip transform
- auto/manual exposure, exposure time, analogue gain, exposure compensation
- AE metering, AE exposure mode, and AE constraint mode when supported by libcamera
- auto/manual white balance, AWB mode, manual colour gains, AWB settle delay
- brightness, contrast, saturation, sharpness
- noise reduction mode when supported
- optional scaler crop
- capture path selection: request/PIL visual path or raw array diagnostic path

Use `GET /api/camera/capabilities` or `python3 scripts/dump_camera_capabilities.py --hardware` to see what the connected camera exposes. Not every libcamera control is guaranteed on every camera module; unsupported values should report a PiSD warning/error code rather than crash.


---

## PiSD 0.1.1 motor channel calibration

Motor wiring differs between cars, so use the one-by-one channel test before assuming a car's direction settings are correct.

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output
```

The script tests one side at a time and stops after every step. `direction_1` means the first pin in that side's pin pair is active; `direction_2` means the second pin is active.

The API equivalent is:

```text
POST /api/motor/test-channel
```

Hardware-enabled API calls must include:

```json
{ "enable_motor_output": true }
```

Without that field, PiSD refuses the channel test with `PISD-MOT-008`.
