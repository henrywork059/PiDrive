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
