# PATCH NOTES - CustomDrive 0_1_0

## Goal
Turn the original CustomDrive draft into a more usable runtime by filling the main placeholders with real PiDrive integrations wherever possible.

## Main problem found
The previous draft README claimed a `live` mode, but the shipped entrypoints still always launched the simulation-only runtime. The bridge also still assumed an older motor API and did not actually match the current PiServer `MotorService.update(..., steer_mix=...)` call shape.

## What was changed

### 1. Added a real live runtime
- Added `custom_drive/live_runtime.py`.
- Live mode now boots the existing sibling PiServer `CameraService` and `MotorService` directly.
- The mission controller now receives real camera-driven perception frames in live mode.
- Terminal and web entrypoints can now explicitly request `sim` or `live` mode.

### 2. Filled the perception placeholder with a configurable detector
- Added `custom_drive/perception.py`.
- Implemented HSV color-based object proposal generation for `he3` and `he3_zone`.
- Added configurable morphology, area thresholds, and per-label HSV ranges.
- Added defaults into `CustomDrive/config/runtime_settings.json` and `custom_drive/runtime_settings.py`.

### 3. Fixed the PiCar bridge so it matches current PiDrive code better
- Reworked `custom_drive/picar_bridge.py`.
- The bridge now tries PiServer-style `steer_mix` calls first and gracefully falls back to older call signatures.
- Added motor action logging with mapped left/right outputs where available.
- Added safer handling for optional arm actions and generic method-name fallbacks.
- Added optional `allow_virtual_grab_without_arm` for route-testing without a real gripper.

### 4. Upgraded the web monitor
- Reworked `custom_drive/web_app.py`.
- Added runtime selection + safe fallback from live to sim.
- Added `/api/frame.jpg` for live camera display.
- Added `/api/settings` load/save endpoints for the shared runtime settings file.
- Updated the web UI to show actual live video in live mode, plus detection overlay and runtime mode notes.

### 5. Upgraded the terminal entrypoint
- Reworked `run_custom_drive_demo.py`.
- Added CLI args for `--mode`, `--cycles`, and `--tick`.
- Terminal output now reports effective mode, fallback notes, and live camera status when relevant.

### 6. Documentation update
- Updated `CustomDrive/README.md` so it now matches the real code path.
- Documented what is now real versus what is still intentionally placeholder.

## What is still not fully solved
- There is still no bundled learned object detector in CustomDrive itself.
- There is still no real arm/gripper driver inside this folder.
- The timed route legs are still rough defaults and still need field calibration.
- The color detector needs HSV tuning for your actual markers, lighting, and camera exposure.

## Why this approach was used
This patch reuses as much of the existing PiDrive stack as possible instead of inventing a parallel runtime:
- PiServer already had a working camera service,
- PiServer already had a working motor mixer,
- CustomDrive already had the mission state machine.

So the patch mainly connected those pieces and filled the missing perception/runtime glue.

## Verification done
- `python -m compileall CustomDrive`
- smoke run: `python CustomDrive/run_custom_drive_demo.py --mode sim --cycles 1 --tick 0.05`
- smoke start check in `CustomDrive/`: instantiate `LiveMissionRuntime(max_cycles=1)`, call `start()` and `step()` twice, then `close()` (verifies the live runtime starts, reuses PiServer services, and handles missing camera hardware safely)

## Recommended next patch
- bind the real grab/release hardware
- add a simple calibration page for HSV target tuning
- optionally consume CustomTrainer detector outputs instead of only color thresholds
- add a mission-specific obstacle or marker subroutine for competition field recovery
