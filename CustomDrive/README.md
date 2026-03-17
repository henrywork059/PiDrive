# CustomDrive

CustomDrive is a mission-controller scaffold for competition-style autonomous tasks.

It focuses on a repeatable mission loop:

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
python run_custom_drive_demo.py
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

## Integration intent

The scaffold is designed to be wired into an existing Pi camera/motor stack later via `picar_bridge.py` and real detection/perception adapters.

## Current limitations

This package does not yet include:

- real detector inference
- real gripper/arm hardware driver
- obstacle avoidance
- odometry/IMU-based recovery
