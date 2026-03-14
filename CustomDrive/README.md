# CustomDrive

CustomDrive is a **draft mission-control package** for the PiCar competition side-quest.
It focuses on **one autonomous mission only**:

1. drive from start to a rough pickup/search area
2. rotate and search for the target resource with object detection
3. visually align and approach the target
4. grab the target
5. drive to a rough drop/search area
6. rotate and search for the collection zone
7. visually align and approach the drop zone
8. release the target
9. repeat

This package is designed as a **clean scaffold** that can later be wired into the current PiServer / PiCar codebase.
It does **not** contain a real detector or real gripper driver yet. Instead, it gives you:

- a mission state machine
- timed coarse routes
- visual-servo control logic
- PiCar bridge stubs for your existing motor / camera stack
- a runnable simulation demo so you can test the logic flow on a PC

## Folder layout

```text
CustomDrive/
├── README.md
├── requirements.txt
├── run_custom_drive_demo.py
├── custom_drive/
│   ├── __init__.py
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
    └── PATCH_NOTES_CustomDrive_draft.md
```

## Main ideas in this draft

### 1. Two-level control

The code intentionally uses two levels of control:

- **coarse route**: a fixed timed route to reach a rough search region
- **fine vision control**: center the detection and approach it slowly

This matches your plan and is much safer than relying on one AI model to do everything.

### 2. Better than raw `(x, y)` minimisation

The final control logic does **not** simply drive the object to the bottom-middle point by raw x/y distance.
Instead it uses:

- **bottom-center of the bounding box** as the target anchor
- **x error** for left-right heading correction
- **bottom position / area ratio** as the close-enough cue

That is usually more stable for real cameras.

### 3. One mission only

The code is configured around a single target label and a single drop-zone label:

- `target_label = "he3"`
- `drop_zone_label = "he3_zone"`

You can rename these labels to match whatever your object detector outputs.

## What is runnable now

You can run the included simulation demo on a PC:

```bash
python run_custom_drive_demo.py
```

The demo fakes detections and prints state changes, so you can see the full mission flow without real hardware.

## How to integrate with your PiCar code later

The expected integration path is:

1. keep your current `camera.py` for live frames
2. keep your current `motor_controller.py` for differential drive
3. add a real object detector adapter
4. add a real arm / gripper driver
5. call `MissionController.update()` from a loop or background task
6. add a `custom_drive` mode to your server / UI later

A draft bridge class is already included in:

- `custom_drive/picar_bridge.py`

## Expected detector output

The mission controller expects per-frame detections with:

- label
- confidence
- bounding box `(x1, y1, x2, y2)` in pixels

The controller does not care whether the detector is YOLO, TFLite, OpenCV-DNN, or something else.

## Important limitations

This is a **draft scaffold**, not a finished field-ready stack.

Missing pieces on purpose:

- real detector inference
- real arm inverse kinematics / servo control
- pickup success sensing
- drop success sensing
- recovery using odometry / IMU
- obstacle avoidance logic
- rules-specific field calibration

## Suggested next real implementation steps

1. connect real detector output into `FramePerception`
2. add a real `pickup_sequence()` and `release_sequence()`
3. replace timed route scripts with field-calibrated route segments
4. add a retry / re-scan strategy after failed grasp
5. later integrate the mode into PiServer web control
