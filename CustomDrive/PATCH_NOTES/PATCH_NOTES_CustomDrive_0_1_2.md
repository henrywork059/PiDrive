# PATCH NOTES — CustomDrive 0_1_2

## Summary
This patch focuses on **robustness, debugging, and easier maintenance** for CustomDrive.

It does **not** change the high-level mission design. Instead, it tightens the runtime plumbing so the package is safer to launch, easier to diagnose, and less likely to fail in confusing ways.

## Main fixes and improvements

### 1) Safer config file handling
- Fixed the config path handling so `run_settings.json` and `runtime_settings.json` are resolved relative to the **CustomDrive folder itself**, not by assuming a specific repo nesting pattern.
- Added stronger normalization/clamping for both config files.
- Invalid values now fall back to safe defaults instead of silently breaking runtime behavior.

### 2) `sim` mode no longer depends on `live` imports
- Fixed a startup bug where importing the runtime factory could fail if `PiServer` or Raspberry Pi-only modules were missing.
- `live` runtime is now imported lazily.
- Result: **simulation mode can run cleanly on a PC even when Pi-only modules are unavailable**.

### 3) Better fallback behavior for `live`
- If `live` mode cannot import or initialize PiServer services, CustomDrive now falls back to `sim` with a clearer reason string.
- This makes headless and GUI launches easier to diagnose.

### 4) Added bounded debug/event history
- Added a lightweight internal debug event buffer.
- State changes, retries, route-leg transitions, runtime resets, background loop start/stop, and camera/runtime warnings are now recorded.
- The GUI now includes a **Debug Trace** panel.
- Headless mode can print debug entries with `--show-debug`.

### 5) Improved mission-controller traceability
- Mission start, state transitions, retry escalation, route-leg changes, and detection events are now recorded as structured debug events.
- Route-start failures now move the mission into a clearer failed state instead of failing unclearly.

### 6) Fixed approach-speed bug
- `visual_servo.py` had an approach-command bug where the throttle logic effectively collapsed to `0` or only the final approach speed.
- The approach logic now:
  - stops to re-center when the target is too far off-center
  - uses normal approach speed when centered enough
  - uses final approach speed when tightly centered

### 7) Runtime lifecycle cleanup
- Improved reset/start/stop handling in both sim and live runtimes.
- Starting after a completed/failed run now resets more predictably.
- Background-thread state is cleaned up more safely.

### 8) Better motor bridge robustness
- `PiCarRobotBridge` now records motor/stop errors instead of failing silently.
- Motor errors are exposed through runtime status for easier diagnosis.

### 9) Better GUI-side resilience
- Added safer API status building in the Flask app.
- Added better frontend fetch error handling.
- GUI now shows runtime errors, motor errors, camera errors, fallback notes, and debug trace output more clearly.

### 10) Better launcher error reporting
- `run_custom_drive_web.py` now gives a clearer message when Flask is missing instead of crashing with a raw import traceback.

## Files changed
- `CustomDrive/README.md`
- `CustomDrive/config/runtime_settings.json`
- `CustomDrive/custom_drive/debug_tools.py` **(new)**
- `CustomDrive/custom_drive/demo_runtime.py`
- `CustomDrive/custom_drive/live_runtime.py`
- `CustomDrive/custom_drive/mission_controller.py`
- `CustomDrive/custom_drive/picar_bridge.py`
- `CustomDrive/custom_drive/run_settings.py`
- `CustomDrive/custom_drive/runtime_factory.py`
- `CustomDrive/custom_drive/runtime_settings.py`
- `CustomDrive/custom_drive/visual_servo.py`
- `CustomDrive/custom_drive/web_app.py`
- `CustomDrive/custom_drive/web/static/app.js`
- `CustomDrive/custom_drive/web/static/styles.css`
- `CustomDrive/custom_drive/web/templates/index.html`
- `CustomDrive/run_custom_drive_demo.py`
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_2.md`

## Verification performed
- `python -m compileall CustomDrive`
- headless sim smoke test
- isolated-folder test confirming:
  - `sim` works without PiServer present
  - `live` falls back cleanly to `sim` when PiServer is unavailable

## Notes / remaining limits
- I could not fully run the Flask GUI end-to-end in this container because `Flask` is not installed here.
- I did not add a real arm/gripper driver in this patch.
- Live-field route timing still needs calibration on the real car.
- HSV detection is still heuristic and may need tuning for your lighting and marker colors.

## Suggested next step
Best next improvement: add a small **runtime settings editor page** in the GUI for camera, motor, and HSV ranges, so field tuning does not require manual JSON edits.
