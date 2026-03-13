# PATCH NOTES — PiServer_0_2_7

## Goal
Review the current PiServer code after the `0_2_0` baseline, harden the startup/control path, reduce unnecessary control-loop work, and add focused tests to prevent regressions.

## Main fixes
- Rebuilt the core startup path into one consistent set so `server.py -> piserver -> piserver.app -> services` does not fail because of mixed partial patches.
- Adopted the newer hardened `ControlService` pattern:
  - `_parse_float` now preserves existing values on malformed numeric inputs.
  - camera processing enable/disable is cached and only updated when the desired state changes.
  - algorithm failures now fall back to safe zero outputs and a descriptive `system_message`.
  - motor failures now hard-stop the outputs and also zero the applied steering/throttle in state.
- Added `invalidate_processing_state_cache()` so camera processing state is reapplied after camera config changes or reloads.
- Added a timed thread join in `ControlService.stop()` to make shutdown/restart cleaner.
- Made `services/__init__.py` lightweight to avoid eager import traps.
- Added `atexit` cleanup in `piserver/app.py` so control/camera/motor services are stopped more cleanly when the process exits.
- Kept the working `MotorService` implementation with direction / max speed / bias support as part of this cumulative repair patch.

## Tests added
Added `PiServer/tests/test_control_service.py` covering:
- invalid manual numeric input handling
- invalid runtime numeric input handling
- camera processing toggle caching behavior
- algorithm exception fallback behavior
- motor exception safe-stop behavior
- processing cache invalidation after camera apply

## Files included in this patch
- `PiServer/server.py`
- `PiServer/piserver/__init__.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/__init__.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/tests/test_control_service.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_7.md`

## Validation performed here
- Python compile check on all patched files
- unit test run for the new `tests/test_control_service.py`

## Notes for Pi validation
After copying the patch files onto the Pi:
1. Run `python3 server.py`
2. Open the web UI and confirm startup works
3. Test manual driving / E-stop / motor settings
4. Run:
   - `python3 -m unittest discover -s tests -v`
   - `python3 -m compileall piserver tests`
