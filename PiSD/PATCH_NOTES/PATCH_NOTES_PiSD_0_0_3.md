# PATCH NOTES - PiSD_0_0_3

## Request summary

User asked to make sure PiSD code and future code include bug/error detection and reporting, with corresponding error codes.

## Cause / gap

PiSD_0_0_2 had safe camera and motor service scaffolding, but many responses and script failures could still be plain text or `{ok/message}` style only. There was no shared error-code registry, no common error-report shape, and no written rule for future PiSD code.

## Files changed

### New files

- `PiSD/pisd/core/errors.py`
- `PiSD/scripts/check_error_reporting.py`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/FUTURE_CODE_RULES.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_3.md`

### Updated files

- `PiSD/PiSD.py`
- `PiSD/README.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/services/motor_service.py`
- `PiSD/scripts/check_service_imports.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/scripts/test_camera_service.py`
- `PiSD/scripts/test_live_http_api.py`
- `PiSD/scripts/test_motor_service.py`

## Behavior changed

### Shared error-code system

Added `pisd/core/errors.py` with:

- `PiSDErrorCodes`
- `ErrorReport`
- `ErrorReporter`
- `ok_payload()`
- `report_payload()`

Current code prefixes:

- `PISD-OK-*`
- `PISD-APP-*`
- `PISD-API-*`
- `PISD-CAM-*`
- `PISD-MOT-*`
- `PISD-TEST-*`

### Service status reporting

Camera and motor status now include:

- `last_error_code`
- `last_error`
- `last_error_severity`
- `recent_errors`

### API response reporting

JSON API endpoints now return a `code` field for success and failure responses.

Added diagnostic endpoints:

```text
GET  /api/errors
POST /api/errors/clear
```

Invalid JSON now reports:

```text
PISD-API-001
```

Missing routes report:

```text
PISD-API-003
```

Unhandled API exceptions report:

```text
PISD-API-004
```

### Camera service error detection

Camera service now records codes for:

- Picamera2 missing
- Picamera2 open failure
- camera control apply failure
- capture failure
- JPEG encode failure
- no frame available
- camera stop/close failure

### Motor service error detection

Motor service now records codes for:

- missing GPIO library
- GPIO/PWM setup failure
- motor output failure
- motor stop failure
- motor close/GPIO cleanup failure
- invalid motor settings payload

### Test script reporting

Test scripts now use PiSD codes for failure cases rather than plain `ERROR:` messages.

Added:

```bash
python scripts/check_error_reporting.py
```

This checks the shared error-report schema without needing Flask or Pi hardware.

## Documentation changed

Added:

- `docs/ERROR_CODES.md` — complete current error-code registry and response format.
- `docs/FUTURE_CODE_RULES.md` — required rules for future code, folder placement, API response shape, and testing expectations.

Updated existing docs to mention:

- `pisd/core/errors.py`
- `/api/errors`
- `/api/errors/clear`
- `scripts/check_error_reporting.py`
- future code must include structured error codes.

## Verification actually performed

From inside `PiSD/`:

```bash
python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/check_service_imports.py
python3 scripts/test_camera_service.py --seconds 1 --min-frames 1
python3 scripts/test_motor_service.py --duration 0.05
```

Results:

- Python compile check passed.
- `PiSD.py --status-only` returned JSON with `code: PISD-OK-000`.
- Error-reporting schema check passed.
- Service import check ran and reported optional dependency availability.
- Camera simulation produced a JPEG frame.
- Motor simulation mapping ran and stopped cleanly.

## Verification not performed

- Flask API test was not run in this local packaging environment because Flask is not installed here.
- Real Raspberry Pi camera hardware was not tested here.
- Real GPIO/motor output was not tested here.

After installing dependencies on the Pi or PC, run:

```bash
python -m pip install -r requirements.txt
python scripts/test_api_endpoints.py
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

Only run real motor output when the wheels are lifted and safe:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

## Known limits / next steps

- The GUI remains a small test shell, not the final PiServer replacement UI.
- Error codes are now established, but future features must keep expanding `PiSDErrorCodes` and `docs/ERROR_CODES.md` together.
- Runtime persistent settings are still not added.
- Real hardware verification must be performed on the Raspberry Pi.
