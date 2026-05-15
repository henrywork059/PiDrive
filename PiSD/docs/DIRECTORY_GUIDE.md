# PiSD Directory, File, and Patch Instructions

## Purpose

This document records how the `PiSD/` folder should be developed so it remains a clean test path for improving PiServer GUI and functions.

## Top-level rules

- Keep all PiSD work inside `PiSD/`.
- Do not modify `PiServer/` from a PiSD patch unless explicitly requested.
- Do not copy old PiServer files blindly.
- Use PiServer as a behavior reference, then rebuild in PiSD with clearer boundaries.
- Keep only one Python dependency file: `PiSD/requirements.txt`.
- Keep all patch notes in `PiSD/PATCH_NOTES/`.
- Put runnable diagnostics in `PiSD/scripts/`.
- Put generated diagnostic files in `PiSD/test_outputs/`.

## Folder instructions

### `PiSD.py`

Main launcher only. It should parse CLI flags and call the package app factory.

Do not place large service logic here.

### `config/`

Stores safe default settings.

Rules:

- keep defaults conservative
- do not store user runtime data here unless a future config store is intentionally added
- preserve backward compatibility when adding keys

### `pisd/app.py`

Owns Flask route wiring and the temporary testing server GUI/API shell.

Rules:

- route handlers should call services
- route handlers should not directly control GPIO or camera hardware
- every hardware action should return clear JSON status
- every JSON response must include a PiSD `code` field
- caught errors should use `pisd.core.errors` instead of plain text-only messages

### `pisd/web/`

Contains browser testing GUI files.

Current files:

- `templates/testing_server.html` — temporary API/settings test page
- `static/css/testing_server.css` — testing page styles
- `static/js/testing_server.js` — testing page API caller logic

Rules:

- keep this as a temporary testing interface until the final GUI is designed
- every action should call an API endpoint rather than bypassing the backend
- display returned `PISD-*` codes clearly
- real motor output must remain locked unless explicitly armed

### `pisd/services/`

Owns real runtime behavior.

Current services:

- `camera_service.py`
- `motor_service.py`

Rules:

- each service must have simulation fallback
- no service should crash on a PC just because Raspberry Pi libraries are missing
- hardware should be opt-in through the launcher until safety is verified

### `pisd/core/`

Small shared helpers only.

Current helpers:

- `value_utils.py` — parsing, clamping, and direction helpers
- `errors.py` — shared PiSD error codes, error history, and API payload helpers

Rules:

- keep helpers generic
- avoid UI or hardware code here
- add new error codes in `errors.py` and document them in `docs/ERROR_CODES.md`

### `scripts/`

Runnable service and API checks.

Current scripts:

- `check_service_imports.py` — imports services, loads defaults, and creates the Flask app factory
- `test_camera_service.py` — starts camera service and saves a JPEG frame
- `test_motor_service.py` — checks motor mapping and optional real GPIO output
- `test_motor_channels.py` — tests left/right motors one by one, raw direction 1/2, multiple speeds, and automatic stop
- `test_api_endpoints.py` — checks API route calls with Flask's test client
- `test_live_http_api.py` — checks HTTP calls against a running PiSD server
- `check_error_reporting.py` — verifies shared error-code/reporting schema without Flask or hardware

Rules:

- scripts must be safe by default
- real motor output must require an explicit flag
- scripts should print JSON-like status useful for debugging
- scripts should exit with non-zero status when a required check fails
- failing scripts should include a `PISD-TEST-*` code, not just a plain text error

### `test_outputs/`

Generated outputs from local service tests.

Rules:

- keep only small diagnostic files here
- do not rely on files here as source code
- it is safe to delete generated files between tests

### `docs/`

Planning and instruction documents.

Rules:

- update docs when run commands, paths, endpoints, or service behavior changes
- remove stale instructions instead of leaving multiple conflicting commands

### `PATCH_NOTES/`

One patch note per package version.

Patch notes must include:

- request summary
- cause/root cause if known
- files changed
- behavior changed
- verification actually performed
- known limits or next steps

## Patch packaging instructions

For PiSD patch zips:

- preserve exact folder structure beginning with `PiSD/`
- after stable `PiSD_0_1_0`, use patch-only delivery unless the user explicitly asks for a full package
- do not add extra nesting such as `PiSD_0_0_3/PiSD/`
- do not include unrelated PiDrive folders

## Anti-rollback checks

Before packaging:

- confirm `requirements.txt` is the only dependency file
- confirm `PiSD.py` still launches the app
- confirm `/api/control/stop` still exists
- confirm camera and motor services still have simulation fallback
- confirm service test scripts exist under `PiSD/scripts/`
- confirm `pisd/core/errors.py` exists and API JSON responses include `code` fields
- confirm docs do not reference removed `requirement.txt`

## Patch 0.0.4 colour diagnostic files

Additional test scripts:

```text
PiSD/scripts/diagnose_camera_color.py
PiSD/scripts/test_motor_channels.py
```

Generated output directory:

```text
PiSD/test_outputs/camera_color/
```

These generated files are for local Pi testing only and should not be committed into future source patches unless the user explicitly asks to include sample captures.

---

## PiSD 0.0.5 camera setting files

- `docs/CAMERA_SETTINGS.md` documents all currently exposed PiSD camera settings and test commands.
- `scripts/dump_camera_capabilities.py` prints Picamera2 camera controls, properties, and sensor modes.
- `scripts/test_camera_settings_matrix.py` runs a repeatable set of size, quality, buffer, exposure, white balance, colour, flip, and noise-reduction checks.
- `scripts/test_camera_service.py` accepts command-line overrides for the main camera settings, so individual controls can be tested without editing code.
- `scripts/diagnose_camera_color.py` now keeps array colour tests optional because the array path is diagnostic/CV-only, not the visual reference.


## Patch 0.1.1 motor calibration files

New test script:

```text
PiSD/scripts/test_motor_channels.py
```

New documentation:

```text
PiSD/docs/MOTOR_CALIBRATION.md
```

Generated output directory:

```text
PiSD/test_outputs/motor_channels/
```

The motor channel test must remain safe by default. Real movement requires explicit hardware flags and the script must stop after every channel step.
