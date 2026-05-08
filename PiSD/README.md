# PiSD

PiSD is a clean new sandbox under `PiDrive/PiSD` for rebuilding, developing, and testing the next PiServer GUI and runtime functions from square one.

It is intentionally separate from the existing `PiServer/` folder so experiments can be tested without rolling back or damaging accepted PiServer work.

## Current status

Version: `0.0.0-placeholder`

This first package contains documentation, a possible Python package list, and one placeholder launcher:

```text
PiSD/
├── PiSD.py
├── README.md
├── requirement.txt
├── requirements.txt
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_PLAN.md
│   ├── GUI_FUNCTION_SPEC.md
│   └── TEST_PLAN.md
└── PATCH_NOTES/
    └── PATCH_NOTES_PiSD_0_0_0.md
```

## Run the placeholder

From the repo root:

```bash
cd PiSD
python PiSD.py
```

Then open:

```text
http://127.0.0.1:5050
```

For LAN testing on the Raspberry Pi:

```bash
python PiSD.py --host 0.0.0.0 --port 5050
```

Status-only check:

```bash
python PiSD.py --status-only
```

## Install possible packages

A requested singular file is included:

```bash
python -m pip install -r requirement.txt
```

A standard plural alias is also included:

```bash
python -m pip install -r requirements.txt
```

On Raspberry Pi OS, install Pi camera packages through `apt` first when camera work begins:

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-libcamera python3-opencv
```

## Development goal

PiSD should be used to prototype the improved PiServer direction in small layers:

1. GUI layout and panel structure.
2. Simulated runtime state.
3. API endpoints.
4. Camera preview pipeline.
5. Motor/control simulation.
6. Real Pi hardware adapters.
7. Model/autonomy testing.
8. Recorder/snapshot/data capture tools.
9. Settings persistence.
10. Final merge or replacement decision for PiServer.

## Important boundary

PiSD is not yet the replacement for `PiServer/`.

It is a clean development branch/folder to test ideas first. Once a function is stable in PiSD, it can be moved back into PiServer or used as the base for a future new server component.
