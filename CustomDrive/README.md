# CustomDrive

CustomDrive is a mission-controller package for competition-style autonomous tasks.

It runs the same finite-state mission loop in two mirrored modes:

1. **No GUI (terminal-first)** for lowest overhead and quickest iteration.
2. **Web GUI (PiServer-style)** for live observability and operator control.

## Mission loop

1. navigate to search area
2. detect and align to target
3. approach + pickup
4. navigate to drop area
5. detect and align to drop zone
6. approach + release
7. repeat by configured cycle count

## Layout

```text
CustomDrive/
├── run_custom_drive_demo.py
├── run_custom_drive_web.py
├── custom_drive/
│   ├── config.py
│   ├── models.py
│   ├── interfaces.py
│   ├── mission_state.py
│   ├── route_script.py
│   ├── visual_servo.py
│   ├── mission_controller.py
│   ├── fake_robot.py
│   ├── demo_runtime.py
│   ├── web_app.py
│   ├── web/
│   │   ├── templates/index.html
│   │   └── static/{app.js,styles.css}
│   └── picar_bridge.py
└── PATCH_NOTES/
```

## Run demo (no GUI, best performance)

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode sim --cycles 2
```

This is the terminal-only runner and remains the fastest path for profiling logic without web overhead.

## Run web GUI demo (PiServer-style monitoring)

```bash
cd CustomDrive
python run_custom_drive_web.py
```

Then open `http://localhost:5050` to:

- start/stop continuous mission stepping
- run single-step updates for debugging
- reset mission with a different cycle count
- see mission state, drive command, detection boxes, and robot action logs

Both the terminal and web entry points use the same `DemoMissionRuntime`, so behavior stays mirrored between GUI and no-GUI flows.

```bash
cd CustomDrive
python run_custom_drive_demo.py --mode live --cycles 2
```

## Run Web GUI

### Simulation mode

```bash
cd CustomDrive
python run_custom_drive_web.py
```

Open `http://localhost:5050`.

### Live mode

```bash
cd CustomDrive
CUSTOMDRIVE_MODE=live python run_custom_drive_web.py
```

Open `http://localhost:5050` and verify:

- mission state and command telemetry updates
- video feed is live in the right panel
- Start/Stop/Step/Reset controls work
- Settings can be saved and reused in terminal mode

## Notes

- In `live` mode, perception uses camera frames and color-based object proposals for `he3` and `he3_zone` labels.
- If camera/GPIO dependencies are unavailable, runtime falls back to `sim` safely.
- Terminal and GUI entrypoints both run the same mission controller logic, so behaviour stays mirrored.
