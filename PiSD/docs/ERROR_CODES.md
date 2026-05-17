# PiSD Error Codes and Reporting Rules

## Purpose

Every PiSD code path should detect, report, and expose errors in a consistent way. New features must not fail silently.

PiSD error reports use this JSON shape:

```json
{
  "ok": false,
  "code": "PISD-CAM-002",
  "message": "Failed to open Picamera2: ...",
  "error": {
    "code": "PISD-CAM-002",
    "message": "Failed to open Picamera2: ...",
    "component": "camera",
    "severity": "error",
    "timestamp_utc": "2026-05-08T00:00:00+00:00",
    "context": {}
  }
}
```

Successful JSON responses should include:

```json
{
  "ok": true,
  "code": "PISD-OK-000",
  "message": "OK"
}
```

Warnings may return `ok: true` with a non-OK code when the service recovered safely, for example when real hardware is unavailable and the service falls back to simulation.

## Error-code prefixes

| Prefix | Area | Example use |
|---|---|---|
| `PISD-OK` | success | successful API or service response |
| `PISD-APP` | launcher/config/app setup | missing dependency, config load failure |
| `PISD-API` | HTTP/API layer | invalid JSON, unhandled route exception |
| `PISD-CAM` | camera service | Picamera2 missing, open/capture/encode failure |
| `PISD-MOT` | motor service | GPIO missing, PWM setup/output/stop failure |
| `PISD-TEST` | test scripts | expected frame missing, API schema missing |

## Current codes

### General

- `PISD-OK-000` — operation completed successfully.

### App / launcher

- `PISD-APP-001` — default config could not be loaded or was invalid.
- `PISD-APP-002` — required app dependency is missing, such as Flask.
- `PISD-APP-003` — launcher startup failed.

### API

- `PISD-API-001` — request body is invalid JSON or not a JSON object.
- `PISD-API-002` — API route caught a service exception.
- `PISD-API-003` — route not found.
- `PISD-API-004` — unhandled API exception.

### Camera

- `PISD-CAM-001` — Picamera2 is missing; simulation fallback used when possible.
- `PISD-CAM-002` — Picamera2 failed to open.
- `PISD-CAM-003` — camera controls failed to apply.
- `PISD-CAM-004` — frame capture failed.
- `PISD-CAM-005` — JPEG encoding failed.
- `PISD-CAM-006` — no JPEG frame available.
- `PISD-CAM-007` — camera stop/close failed.

### Motor

- `PISD-MOT-001` — GPIO library is missing; simulation fallback used when possible.
- `PISD-MOT-002` — GPIO/PWM setup failed.
- `PISD-MOT-003` — motor output update failed.
- `PISD-MOT-004` — motor stop command failed.
- `PISD-MOT-005` — motor close/GPIO cleanup failed.
- `PISD-MOT-006` — motor config payload was invalid.

### Test scripts

- `PISD-TEST-001` — import check failed.
- `PISD-TEST-002` — camera test did not produce the expected frame.
- `PISD-TEST-003` — motor test did not stop cleanly.
- `PISD-TEST-004` — API/error-reporting schema check failed.

## Required pattern for future code

1. Import shared helpers from `pisd.core.errors`.
2. Do not return plain `{ok: false, message: ...}` without a `code`.
3. Do not print plain `ERROR:` in scripts. Include a PiSD code.
4. Add enough `context` to make the problem debuggable, but do not include passwords or secrets.
5. Service status must include at least:
   - `last_error_code`
   - `last_error`
   - `last_error_severity`
   - `recent_errors`
6. API JSON responses must include at least:
   - `ok`
   - `code`
   - `message`
7. Catch recoverable hardware errors and report them instead of crashing the GUI.
8. Crash only when the program cannot safely continue.

## Diagnostic API endpoints

```text
GET  /api/errors
POST /api/errors/clear
```

`/api/status` also includes recent app, camera, and motor errors.

## Patch 0.0.4 camera colour diagnostic additions

Additional codes:

| Code | Component | Meaning |
|---|---|---|
| `PISD-CAM-008` | Camera | Camera colour control, AWB mode, or array colour-order handling warning/failure. |
| `PISD-TEST-005` | Test | Camera colour diagnostic script failed to save one or more expected frames. |

Colour-control warnings are normally non-fatal. They should appear in `recent_errors` and `/api/errors` so the user can see exactly which setting was ignored or failed.

---

## PiSD 0.0.5 added camera setting codes

- `PISD-CAM-009` — camera setting was invalid, unknown, ignored, or only partly applicable.
- `PISD-CAM-010` — camera capability query failed.
- `PISD-TEST-006` — camera settings matrix test failed.


---

## PiSD 0.1.1 added motor calibration codes

- `PISD-MOT-007` — motor channel test input was invalid, such as an unknown side or too-low speed.
- `PISD-MOT-008` — live API motor channel test was not armed with `enable_motor_output: true`.
- `PISD-MOT-009` — motor channel test output command failed.
- `PISD-TEST-007` — `scripts/test_motor_channels.py` detected one or more failed channel-test steps.

The one-by-one motor calibration path must always stop after every step and include a PiSD code in its JSON summary.

---

## PiSD 0.1.2 added standard validation code

- `PISD-TEST-008` — `scripts/run_standard_validation.py` detected one or more failed standard validation checks, or the validation script itself hit an unexpected exception.

The standard validation script prints one simple line per function, for example:

```text
OK   PISD-OK-000   camera.service_frame - frame captured (12345 bytes)
FAIL PISD-TEST-002 camera.service_frame - camera frame failed: ...
```

Use this script as the preferred quick checklist before building or changing the main PiSD server GUI.


## Testing GUI validation

- `PISD-TEST-009` — testing server GUI route or manifest failed local validation.
- `PISD-TEST-010` — testing server GUI template, CSS, JS, or static asset contract failed validation.
- `PISD-TEST-011` — testing server GUI API contract or browser smoke-test sequence failed validation.

The testing GUI must keep visible `PISD-*` response codes and must keep real motor output locked unless the request explicitly includes `enable_motor_output: true`.

## Panel testing GUI validation codes

```text
PISD-TEST-012
```

Meaning: the `/panel-testing` page, static assets, panel registry, style controls, size controls, responsive source contract, or panel manifest failed validation.

Typical check command:

```bash
python3 scripts/test_panel_testing_page.py
```

## PiSD 0.2.4 added panel API contract codes

- `PISD-TEST-013` — panel API contract safe test was intentionally skipped because the panel is a future placeholder, such as Recording/Dataset or Model/Lane Runtime.
- `PISD-TEST-014` — panel API contract map, endpoint declaration, expected-code declaration, or safe panel API action failed validation.

The panel testing page must distinguish three states:

```text
OK   PISD-OK-000   panel.camera_preview.api - HTTP 200
SKIP PISD-TEST-013 panel.recording.placeholder - future placeholder
FAIL PISD-TEST-014 panel.camera_settings.api - expected code mismatch
```

A skipped future placeholder is acceptable before the final GUI stage. A failed contract means the panel cannot be safely wired into the actual GUI yet.


## Main dashboard validation error code

- `PISD-TEST-015` — main dashboard template, CSS, JS, Flask route, static asset, or safe STOP route contract failed validation.

Example:

```text
FAIL PISD-TEST-015 main_dashboard.source_contract - main dashboard source contract failed
```

## Camera FPS test code

- `PISD-TEST-017` — live-frame FPS or camera FPS validation failed. Check `/api/camera/fps-stats`, camera settings, encode time, frame size, and browser/server route availability.

## Added in 0.2.8

```text
PISD-TEST-018
```

Used by panel presentation settings validation and import/error reporting for the browser-local panel presentation page.

## Added in 0.2.9

```text
PISD-TEST-019
```

Used by manual drive page validation when the `/manual-drive` page, its static files, or its required safety/API contracts are missing or invalid.

## PiSD 0.2.10 settings persistence codes

- `PISD-SET-001` — runtime settings file load failed; PiSD falls back to defaults.
- `PISD-SET-002` — runtime settings file save failed.
- `PISD-SET-003` — invalid settings payload, such as an unknown top-level settings group.
- `PISD-SET-004` — saved settings could not be applied to live services.
- `PISD-SET-005` — reset-to-default settings flow failed.
- `PISD-TEST-020` — persistent settings validation or UI contract check failed.

## PiSD 0.3.2 UI presentation consistency code

- `PISD-TEST-021` — unified page/panel presentation validation failed. This is used by `scripts/test_ui_presentation_consistency.py` when a GUI page is missing the shared final stylesheet, or when the shared stylesheet no longer contains the layout fixes for Manual Drive, Settings, Testing, Dashboard, Panel Presentation, and Panel Testing pages.

## PiSD 0.3.5 recording and metadata codes

- `PISD-REC-001` — no camera frame was available for capture/recording.
- `PISD-REC-002` — frame or JSONL metadata write failed.
- `PISD-REC-003` — recording start was refused because a session is already running.
- `PISD-REC-004` — recording stop was requested but no session is running.
- `PISD-REC-005` — recording session folder/manifest creation failed.
- `PISD-REC-006` — recording stop/final manifest write failed.
- `PISD-REC-007` — invalid recording configuration.
- `PISD-TEST-022` — recording service validation failed.

## PiSD 0.3.7 responsive layout test code

- `PISD-TEST-023` — responsive layout contract validation failed. Used by `scripts/test_responsive_layout_contract.py` when a page does not load the shared layout system, the CSS order is wrong, or the Manual Drive semantic panel order is broken.

## PiSD 0.5.2 AI mode codes

- `PISD-AI-001` — AI model id/path was missing, unsafe, unsupported, or not found under `PiSD/models/`.
- `PISD-AI-002` — AI model file was found but could not be loaded by the available runtime backend.
- `PISD-AI-003` — AI preview/drive was requested before a runnable model was loaded.
- `PISD-AI-004` — AI inference failed while reading a camera frame, preprocessing, predicting, or parsing model output.
- `PISD-AI-005` — guarded AI drive was refused because the safety acknowledgement or motor-output arm flag was missing.
- `PISD-AI-006` — AI runtime loop failed or was already running.
- `PISD-TEST-025` — AI Mode page/service validation failed.

PiSD 0.5.2 replaces the earlier scripted Autopilot foundation with AI Mode. AI motor output must pass through the AI safety limiter before reaching `MotorService.update(...)`.


## PiSD 0.5.3 AI mode UI/control note

PiSD 0.5.3 keeps the 0.5.2 AI error-code set, but fixes AI Mode max throttle and fixed throttle limits so the UI, runtime settings, and safety limiter can use the full `0.00` to `1.00` motor-command range. It also aligns AI Mode page styling with Manual Drive panels/buttons.
