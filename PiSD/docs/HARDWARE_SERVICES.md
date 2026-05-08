# PiSD Hardware Service Notes

## Why this patch adds services now

The first PiSD package was a placeholder. This patch adds real service boundaries so camera, motor, and GUI development can be tested through APIs instead of being hardcoded into the page.

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

## Hardware safety

Real hardware is not enabled by default.

Use:

```bash
python PiSD.py --hardware
```

Without `--hardware`, motor commands only update simulated left/right values and print `[PiSD MOTOR SIM]` logs.

## Known limits

- No persistent runtime settings store yet.
- No snapshot folder manager yet.
- No model/autonomy service yet.
- The web UI is still a small test shell, not the final PiServer replacement UI.
