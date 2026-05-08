# PiSD Architecture Notes

## Goal

PiSD is a clean rebuild path for PiServer-style GUI and runtime services.

The design should make every function testable in simulation before connecting real Raspberry Pi hardware.

## Current structure

```text
PiSD/
├── PiSD.py
├── config/defaults.json
├── pisd/app.py
├── pisd/core/value_utils.py
├── pisd/services/camera_service.py
└── pisd/services/motor_service.py
```

## Layer rules

### Launcher layer

`PiSD.py` should only parse arguments and start the app.

### Web/API layer

`pisd/app.py` owns Flask routes and the temporary GUI.

Rules:

- call services through clear methods
- return JSON status for actions
- keep emergency stop reachable
- avoid direct camera/GPIO code in routes

### Service layer

`pisd/services/` owns runtime behavior.

Current services:

- camera service
- motor service

Each service must support:

- real adapter path when hardware is available
- simulation fallback when hardware is unavailable
- clear status output
- safe failure messages

### Core helper layer

`pisd/core/` contains small shared helpers such as value clamping.

## Hardware mode

PiSD defaults to simulation mode. Real adapters are enabled by:

```bash
python PiSD.py --hardware
```

This protects development computers and prevents accidental motor activity.

## Future target structure

Add these only when needed:

```text
pisd/services/settings_service.py
pisd/services/recorder_service.py
pisd/services/model_service.py
pisd/services/autonomy_service.py
pisd/web/static/
pisd/web/templates/
tests/
```
