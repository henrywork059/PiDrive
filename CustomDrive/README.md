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
├── custom_drive/
│   ├── config.py
│   ├── models.py
│   ├── interfaces.py
│   ├── mission_state.py
│   ├── route_script.py
│   ├── visual_servo.py
│   ├── mission_controller.py
│   ├── fake_robot.py
│   └── picar_bridge.py
└── PATCH_NOTES/
```

## Run demo

```bash
cd CustomDrive
python run_custom_drive_demo.py
```

The demo uses `FakeRobot` and scripted detections to exercise state transitions without hardware.

## Integration intent

The scaffold is designed to be wired into an existing Pi camera/motor stack later via `picar_bridge.py` and real detection/perception adapters.

## Current limitations

This package does not yet include:

- real detector inference
- real gripper/arm hardware driver
- obstacle avoidance
- odometry/IMU-based recovery
