# CustomDrive

CustomDrive is a mission-controller package for competition-style autonomous tasks.

It supports **two launch modes** that share the same saved run settings file:

1. **GUI mode** for browser-based monitoring and control.
2. **Headless mode** for running without any display.

Inside either launch mode, the runtime backend can still be either:

- **Simulation (`sim`)** for fast PC-side testing.
- **Live (`live`)** using the existing **PiServer** camera + motor services.

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
- web GUI with live JPEG camera view + detection overlay
- shared runtime settings file for camera / motor / mission perception tuning
- shared **run settings** file used by both GUI mode and headless mode
- debug trace feed for state changes, retries, route-leg changes, and runtime warnings

## What is still placeholder / optional

- there is still **no bundled object-detection model** in CustomDrive itself
- there is still **no bundled real arm/gripper driver** in this folder
- pickup/release can only be truly physical when you bind a real arm object
- coarse route timings still need field calibration on the real course

## Robustness improvements in the current patch line

- `sim` mode no longer depends on importing live PiServer modules first
- malformed `run_settings.json` and `runtime_settings.json` values are normalized and clamped
- headless and GUI launches expose clearer fallback reasons when `live` cannot start
- both runtimes keep a bounded in-memory debug/event history for easier diagnosis
- camera/runtime warnings now surface in GUI status instead of failing silently
- headless runner can print debug trace entries with `--show-debug`

## Layout

```text
CustomDrive/
├── run_custom_drive_demo.py
├── run_custom_drive_web.py
├── run_custom_drive_headless.py
├── run_custom_drive_gui.py
├── run_custom_drive_manual.py
├── config/runtime_settings.json
├── config/run_settings.json
├── config/manual_control.json
├── custom_drive/
│   ├── config.py
│   ├── debug_tools.py
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
│   ├── run_settings.py
│   ├── runtime_factory.py
│   ├── web_app.py
│   ├── manual_control_config.py
│   ├── manual_control_app.py
│   ├── project_paths.py
│   ├── web/
│   └── manual_web/
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

## Launch mode 1: headless

Headless mode runs without displaying a GUI.

```bash
cd CustomDrive
python run_custom_drive_headless.py
```

Compatibility launcher:

```bash
python run_custom_drive_demo.py
```

Optional overrides:

```bash
python run_custom_drive_headless.py --mode live --cycles 2 --tick 0.1 --show-debug
```

If you do not pass overrides, the runner uses:

```text
CustomDrive/config/run_settings.json
```

## Launch mode 2: GUI

GUI mode now starts a fresh PiServer-style **GUI control page**.

```bash
cd CustomDrive
python run_custom_drive_gui.py
```

Compatibility launcher:

```bash
python run_custom_drive_web.py
```

Then open `http://localhost:5050`.

The GUI now shows:

- a live PiServer camera preview
- a full-width status strip
- a right-side manual drive drag pad
- real manual motor output through PiServer `ControlService` in `manual` mode
- a top-right **Settings** button that opens one overlay window
- drive controls for max throttle, steer mix, and steer bias inside that overlay
- PiServer-style appearance settings inside that same overlay

This GUI is intentionally a clean control workspace first. It does not switch modes inside the page.

## Saved run settings

CustomDrive stores launch/run defaults in:

```text
CustomDrive/config/run_settings.json
```

That file is shared by both:

- GUI mode
- headless mode

Current keys:

- `runtime_mode`: `sim` or `live`
- `max_cycles`: default pickup/drop cycles
- `headless_tick_s`: default loop delay for headless mode
- `gui_tick_s`: default GUI auto-run loop delay
- `auto_start_gui`: auto-start mission when GUI opens

## Runtime settings

Hardware and perception tuning live in:

```text
CustomDrive/config/runtime_settings.json
```

Important sections:

- `camera`: forwarded into PiServer `CameraService`
- `motor`: forwarded into PiServer `MotorService`
- `runtime.steer_mix`: steering mix used by the motor bridge
- `runtime.allow_virtual_grab_without_arm`: lets the mission continue without a real arm for route testing only
- `runtime.event_history_limit`: max debug entries kept in memory
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

## Manual control app for competition

CustomDrive also includes a separate **PiServer-style manual control app** for competition driving.

Launch it with:

```bash
cd CustomDrive
python run_custom_drive_manual.py
```

Then open `http://localhost:5050` on the Pi, or `http://<pi-ip>:5050` from another device.

This manual controller:

- reuses PiServer `CameraService`, `MotorService`, `ControlService`, and `runtime.json`
- forces the `manual` algorithm so the real PiServer motor path is used
- keeps a slim PiServer-like header and full-width status strip
- places manual drive on the right side of the page
- polls the PiServer JPEG preview path for lower-friction debugging
- stores manual UI + arm presets in `CustomDrive/config/manual_control.json`
- adds **Up / Down / Hold / Release** arm buttons with optional PCA9685 servo output

Arm notes:

- arm control is disabled by default
- enable and tune it in `CustomDrive/config/manual_control.json`
- the backend uses `adafruit_servokit` when `arm.enabled=true` and `arm.backend="pca9685"`
- `lift_channel` controls up/down and `grip_channel` controls hold/release

That separation keeps autonomous mission control and competition manual driving easier to manage.


## Manual arm control notes (0_1_8)
- `CustomDrive/config/manual_control.json` now enables the arm by default.
- `Up` and `Down` on the manual page are press-and-hold lift controls.
- `Hold` and `Release` are one-tap gripper commands.
- Tune `lift_up_angle`, `lift_down_angle`, and `lift_step_angle` for your hardware.


## GUI control shell

`run_custom_drive_gui.py` now starts a fresh PiServer-style GUI shell for CustomDrive.

Current behavior:
- no mode-selection tabs
- live camera shown on the main page
- style settings page uses the same theme/custom-override pattern as PiServer
- drive/system panels are still placeholders for later wiring

Run:

```bash
cd ~/PiDrive/CustomDrive
python -u run_custom_drive_gui.py
```

Open:
- `http://127.0.0.1:5050` on the Pi
- `http://<pi-ip>:5050` from another device


Top-right GUI buttons:
- Drive Settings
- Style Settings
