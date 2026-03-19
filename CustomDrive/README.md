# CustomDrive

CustomDrive is a mission-controller package for competition-style autonomous tasks. It orchestrates state-machine behavior (search, align, approach, pickup, drop) while allowing both simulation and live Pi runtime modes.

## Launch modes and runtime modes

CustomDrive has **two launch modes** and **two runtime backends**.

### Launch modes

1. **GUI mode** — browser monitoring and controls.
2. **Headless mode** — no GUI, terminal-driven operation.

### Runtime backends

- **`sim`** — PC-side simulation for fast development/testing.
- **`live`** — uses PiServer camera and motor services for real hardware.

Both launch modes share the same saved run settings file.

## Mission loop

1. Navigate to search area.
2. Detect and align to target.
3. Approach and pickup.
4. Navigate to drop area.
5. Detect and align to drop zone.
6. Approach and release.
7. Repeat for configured cycle count.

## Current capabilities

- Live runtime bootstraps PiServer `CameraService` + `MotorService`.
- Live camera polling and motor output bridge.
- Color-range perception support for `he3` and `he3_zone`.
- Web GUI with live JPEG preview + detection overlay.
- Shared runtime settings for camera/motor/perception tuning.
- Shared run settings for GUI and headless launch defaults.
- Debug trace feed for state changes/retries/warnings.

## Current limitations / placeholders

- No bundled object detector model in CustomDrive itself.
- No bundled physical arm/gripper driver in this folder.
- Physical pickup/release requires integrating a real arm interface.
- Coarse route timing still requires on-field calibration.

## Patch-line robustness improvements

- `sim` mode no longer depends on importing live PiServer modules first.
- Malformed run/runtime settings are normalized and clamped.
- GUI/headless startup now provides clearer live-mode fallback reasons.
- In-memory debug/event history is bounded.
- Camera/runtime warnings surface in GUI status.
- Headless runner can print debug trace entries via `--show-debug`.

## Project layout

```text
CustomDrive/
├── run_custom_drive_demo.py
├── run_custom_drive_web.py
├── run_custom_drive_headless.py
├── run_custom_drive_gui.py
├── config/runtime_settings.json
├── config/run_settings.json
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
│   └── web/
└── PATCH_NOTES/
```

## Install

CustomDrive reuses sibling `PiServer/` modules from this repo.

```bash
cd CustomDrive
python -m pip install -r requirements.txt
```

For **live mode**, ensure Pi dependencies are available:

- Flask
- NumPy
- OpenCV
- Picamera2 (for Pi camera)
- RPi.GPIO (for live motor output)

## Launch: headless mode

```bash
cd CustomDrive
python run_custom_drive_headless.py
```

Compatibility launcher:

```bash
python run_custom_drive_demo.py
```

Example with overrides:

```bash
python run_custom_drive_headless.py --mode live --cycles 2 --tick 0.1 --show-debug
```

If no overrides are passed, values are loaded from:

```text
CustomDrive/config/run_settings.json
```

## Launch: GUI mode

```bash
cd CustomDrive
python run_custom_drive_gui.py
```

Compatibility launcher:

```bash
python run_custom_drive_web.py
```

Optional runtime override:

```bash
python run_custom_drive_gui.py --mode sim
```

Then open:

```text
http://localhost:5050
```

## GUI panels and signals

The GUI includes:

- mission state + drive telemetry,
- detection overlays,
- live camera preview in `live` mode,
- robot action logs,
- Saved Run Settings editor,
- Debug Trace panel for warnings/state transitions/fallback notes.

## Run settings (shared)

File:

```text
CustomDrive/config/run_settings.json
```

Used by both GUI and headless runners.

Key fields:

- `runtime_mode`: `sim` or `live`
- `max_cycles`: default mission cycle count
- `headless_tick_s`: default headless loop delay
- `gui_tick_s`: default GUI loop delay
- `auto_start_gui`: auto-start mission on GUI launch

## Runtime settings (tuning)

File:

```text
CustomDrive/config/runtime_settings.json
```

Important sections:

- `camera` — forwarded to PiServer camera service
- `motor` — forwarded to PiServer motor service
- `runtime.steer_mix` — steering mix in motor bridge
- `runtime.allow_virtual_grab_without_arm` — route testing without physical arm
- `runtime.event_history_limit` — max debug entries in memory
- `perception.labels.he3.ranges` and `he3_zone.ranges` — HSV color ranges

Example HSV block:

```json
{
  "lower": [90, 80, 70],
  "upper": [135, 255, 255]
}
```

## Design choice

CustomDrive intentionally uses **coarse route scripting + local visual servoing** (instead of end-to-end driving). This keeps behavior inspectable and easier to debug, and allows future perception source swaps with lower refactor cost.
