# PiSD Test Plan

## Local checks

From inside `PiSD/`:

```bash
python -m py_compile PiSD.py pisd/app.py pisd/core/value_utils.py pisd/services/camera_service.py pisd/services/motor_service.py
python PiSD.py --status-only
```

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
- status JSON returns
- camera can start in simulation
- preview image changes over time
- steering/throttle sliders update motor simulation state
- STOP resets left/right motor output to zero

## Raspberry Pi hardware test

Only run when the car is safe and wheels are lifted or motor power is controlled.

```bash
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Camera checks:

- `/api/camera/start` returns ok
- `/api/camera/frame.jpg` returns a current image
- `/video_feed` streams frames
- `/api/camera/stop` releases the camera

Motor checks:

- `/api/motor/config` reports `adapter: rpigpio`
- small steering/throttle values move the expected motors
- `/api/control/stop` stops outputs immediately
- direction settings can be changed safely if wiring is reversed

## Verification rule

Patch notes must only claim tests that were actually run.
