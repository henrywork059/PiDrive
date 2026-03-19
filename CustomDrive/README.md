# CustomDrive

CustomDrive is a mission-controller package for competition-style autonomous tasks.

It now runs the same finite-state mission loop in two mirrored modes:

1. **Simulation (`sim`)** for fast PC-side state-machine testing.
2. **Live (`live`)** using the existing **PiServer** camera + motor services, with simple color-based perception and the same mission loop.

## Mission loop

1. navigate to search area
2. detect and align to target
3. approach + pickup
4. navigate to drop area
5. detect and align to drop zone
6. approach + release
7. repeat by configured cycle count

## What is real now

- real `live` runtime that boots PiServer `CameraService` and `MotorService`
- real camera frame polling in live mode
- real drive output through the PiServer motor mixer
- configurable color-based perception for `he3` and `he3_zone`
- web monitor with live JPEG camera view + detection overlay
- shared runtime settings file for camera / motor / mission perception tuning

## What is still placeholder / optional

- there is still **no bundled object-detection model** in CustomDrive itself
- there is still **no bundled real arm/gripper driver** in this folder
- pickup/release can only be truly physical when you bind a real arm object
- coarse route timings still need field calibration on the real course

## Layout

```text
CustomDrive/
├── run_custom_drive_demo.py
├── run_custom_drive_web.py
├── config/runtime_settings.json
├── custom_drive/
│   ├── config.py
│   ├── models.py
│   ├── interfaces.py
│   ├── mission_state.py
│   ├── route_script.py
│   ├── visual_servo.py
│   ├── perception.py
│   ├── mission_controller.py
│   ├── fake_robot.py
│   ├── picar_bridge.py
│   ├── demo_runtime.py
│   ├── live_runtime.py
│   ├── runtime_settings.py
│   ├── web_app.py
│   └── web/
└── PATCH_NOTES/
```

## Install

CustomDrive reuses the sibling `PiServer/` package in the same repo.

```bash
cd CustomDrive
python -m pip install -r requirements.txt
```

For **live mode**, make sure the Pi also has the camera/runtime dependencies available through your OS image or Python environment, especially:

- Flask
- NumPy
- OpenCV
- Picamera2 on Raspberry Pi OS when using the Pi camera
- RPi.GPIO when using live motor output

## Run terminal mode

### Simulation

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode sim --cycles 2
```

### Live

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode live --cycles 2
```

Notes:

- `live` mode uses the same state machine, but swaps in PiServer camera/motor services.
- if the camera backend cannot start, the runtime still stays up and reports the camera error in status output
- without a real arm bound, pickup/release still fails by default unless you enable `runtime.allow_virtual_grab_without_arm`

## Run web GUI

### Simulation

```bash
cd CustomDrive
python run_custom_drive_web.py --mode sim
```

### Live

```bash
cd CustomDrive
python run_custom_drive_web.py --mode live
```

Then open `http://localhost:5050`.

The web GUI now shows:

- mission state and drive telemetry
- detection overlays
- live JPEG camera preview in `live` mode
- fallback reason if live mode could not be created
- robot action logs

## Runtime settings

CustomDrive stores settings in:

```text
CustomDrive/config/runtime_settings.json
```

Important sections:

- `camera`: forwarded into PiServer `CameraService`
- `motor`: forwarded into PiServer `MotorService`
- `runtime.steer_mix`: steering mix used by the motor bridge
- `runtime.allow_virtual_grab_without_arm`: lets the mission continue without a real arm for route testing only
- `perception.labels.he3.ranges` / `perception.labels.he3_zone.ranges`: HSV ranges for color detection

Example HSV tuning block:

```json
{
  "lower": [90, 80, 70],
  "upper": [135, 255, 255]
}
```

## Current design choice

The controller still uses **coarse route + local visual servoing** instead of a single end-to-end driving model. That keeps the mission logic easier to debug and makes it possible to swap perception sources later.
