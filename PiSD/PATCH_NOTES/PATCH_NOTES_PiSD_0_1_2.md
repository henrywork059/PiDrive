# PATCH NOTES - PiSD 0.1.2

## Request summary

User requested a standard testing script that reports each function simply as OK or not OK, with a corresponding PiSD error code. User also requested updated testing instructions showing examples of successful OK testing.

## Cause / context

PiSD already had several focused test scripts, but before building the main server GUI it is useful to have one standard checklist that confirms the important direct service and local API-to-hardware paths without reading long JSON output.

The new script is intended to be the first test to run after patches and before larger GUI/server work.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_1_2.md`

## Behaviour changed

Added:

```text
PiSD/scripts/run_standard_validation.py
```

The script prints one simple line per validation item:

```text
OK   PISD-OK-000   config.load_defaults - defaults loaded
OK   PISD-OK-000   camera.service_frame - frame captured (... bytes)
FAIL PISD-TEST-002 camera.service_frame - camera frame failed: ...
```

It also writes a JSON summary to:

```text
PiSD/test_outputs/standard_validation/summary.json
```

## Standard checks covered

The script checks:

- default config loading
- shared error/reporting schema
- camera and motor service import/status wiring
- direct camera service frame capture
- direct camera settings apply + capture
- direct motor one-by-one channel test in simulation, or real hardware when explicitly armed
- local Flask test-client API status
- local API camera start/frame/apply path
- local API motor config path
- local API motor channel path
- local API motor safety refusal when hardware mode is enabled but motor output is not armed
- local API stop endpoint
- invalid JSON error-code response, expected to return `PISD-API-001`

## Safety behaviour

Default run is simulation-safe:

```bash
python3 scripts/run_standard_validation.py
```

Real camera/GPIO adapter check without moving motors:

```bash
python3 scripts/run_standard_validation.py --hardware
```

Real motor output requires both flags:

```bash
python3 scripts/run_standard_validation.py --hardware --enable-motor-output
```

This preserves the existing safety rule that real motor output must be explicitly armed.

## Error reporting

Added:

- `PISD-TEST-008` — standard validation checklist failed, or the standard validation script hit an unexpected exception.

The script still preserves more specific underlying codes where possible, such as:

- `PISD-TEST-002` for missing camera frame
- `PISD-TEST-003` for stop failure
- `PISD-TEST-007` for motor channel failure
- `PISD-API-001` for invalid JSON handling
- `PISD-MOT-008` for safe refusal of unarmed real motor channel testing

## Documentation changed

Updated:

- `docs/TEST_PLAN.md` with standard validation commands and example successful output
- `docs/ERROR_CODES.md` with `PISD-TEST-008`
- `README.md` with the new standard validation workflow

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/run_standard_validation.py --skip-api --motor-speed 0.05 --motor-duration 0.05`
- patch-only zip structure check
- confirmed only changed/new files are included in the patch zip
- confirmed `requirements.txt` remains the only dependency file and `requirement.txt` was not restored

## Not verified here

- Full local Flask API checks, because Flask is not installed in this packaging environment.
- Real Raspberry Pi camera hardware.
- Real GPIO/motor output.

These are intended to be verified on the Pi with:

```bash
python3 scripts/run_standard_validation.py --hardware
python3 scripts/run_standard_validation.py --hardware --enable-motor-output
```

## Known limits / next steps

- The standard script confirms function-call paths, but it cannot judge whether physical wheel direction is correct; that must still be observed by the user or later recorded through the GUI calibration page.
- A future GUI patch should surface this same checklist as a web-based diagnostics page.
