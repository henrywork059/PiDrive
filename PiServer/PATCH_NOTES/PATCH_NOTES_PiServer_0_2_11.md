# PATCH NOTES — PiServer 0_2_11

## Summary
This patch continues the PiServer backend review with a focus on thread safety, safer model handling, and easier-to-maintain shared parsing logic.

It builds on the runtime/config hardening work by reducing cross-thread races between the control loop and web API requests, especially around motor updates and model changes.

---

## Problems addressed

### 1) Motor updates and motor setting changes could race each other
The control loop can call `motor_service.update()` while the web API calls `motor_service.apply_settings()`.
Without a lock, the runtime could see partially-updated motor calibration values or stop/update overlap.

### 2) Model changes were not protected against live inference access
`ModelService.load_model()` could replace the interpreter while autopilot or auto-steer inference was still using it.
That creates a subtle race condition that can be hard to reproduce.

### 3) Uploaded model writes were direct writes to the target path
If an upload was interrupted, the `.tflite` file on disk could be left partially written.
This is especially risky if the uploaded filename matches an existing model.

### 4) Parsing logic was duplicated across services
Boolean, float, and direction parsing existed in multiple places.
That makes future maintenance harder and increases the chance that one code path behaves differently from another.

### 5) Control loop fallback assumed a manual algorithm always exists
The control loop used a direct lookup path that could still fail if the algorithm registry was modified and the `manual` entry was missing.
That is a preventable crash path.

### 6) Config-save endpoint could raise a plain server error
`/api/config/save` did not wrap save failures into a controlled JSON response.

---

## What changed

### Shared parsing helpers
- added `piserver/core/value_utils.py`
- centralized:
  - finite float parsing
  - clamped float parsing
  - integer parsing
  - bool-like parsing
  - motor direction normalization
- updated app/control/motor code to use the shared helpers

### Motor service hardening
- added a lock around:
  - `apply_settings()`
  - `update()`
  - `stop()`
  - persisted-config reads
- malformed motor values now preserve the last good setting instead of forcing bad state
- simulation logging is throttled so non-GPIO runs are less noisy and easier to read

### Model service hardening
- added a lock around interpreter/active-model access
- `load_model()` now only swaps in the interpreter after allocation succeeds
- `predict_uv_from_frame()` now runs against a locked interpreter reference
- uploads now save to a temporary file first and then replace the final `.tflite`
- uploaded filenames are sanitized to basename-only before saving

### Control-service robustness
- added safe algorithm fallback logic:
  - active algorithm if available
  - otherwise `manual`
  - otherwise the first available algorithm
  - otherwise safe idle output
- motor status values are normalized more defensively before being copied into runtime state
- runtime config apply now catches motor-config failures and reports camera-config apply failures more clearly

### API robustness
- `/api/config/save` now returns a controlled JSON error if save fails

### Validation
Added tests for:
- shared parsing helpers
- malformed motor settings preserving last good values
- model upload basename sanitizing and extension validation
- control-loop fallback when `manual` is missing

---

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/value_utils.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/model_service.py`
- `PiServer/tests/test_control_service.py`
- `PiServer/tests/test_motor_service.py`
- `PiServer/tests/test_model_service.py`
- `PiServer/tests/test_value_utils.py`
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_11.md`

---

## Verification performed
- `python3 -m compileall -q .`
- `python3 -m unittest discover -s tests -q`

Both checks passed in the patch workspace.

---

## Notes
- This is a patch-only zip.
- It does not overwrite your existing `config/runtime.json`.
- The focus here is backend/runtime stability and maintainability, not a UI redesign.
