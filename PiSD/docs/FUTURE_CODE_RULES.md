# PiSD Future Code Rules

## Error handling is mandatory

All new PiSD code must include bug/error detection and reporting. New modules should use `pisd.core.errors.ErrorReporter` and the shared `PiSDErrorCodes` registry.

Minimum rule:

```python
from pisd.core.errors import ErrorReporter, PiSDErrorCodes

errors = ErrorReporter("my_component")
try:
    do_work()
except Exception as exc:
    report = errors.report(
        PiSDErrorCodes.API_SERVICE_EXCEPTION,
        f"My component failed: {exc}",
        context={"operation": "do_work"},
        exc=exc,
    )
```

For API responses, use:

```python
from pisd.core.errors import ok_payload, report_payload
```

Do not create a new error-code style unless this document is intentionally updated.

## Folder placement

- Shared error/reporting helpers belong in `pisd/core/`.
- Hardware-specific error detection belongs in the matching service under `pisd/services/`.
- API translation from service result to JSON belongs in `pisd/app.py`.
- Test-script failure codes belong in `scripts/` and should use `PISD-TEST-*`.
- User-facing error-code documentation belongs in `docs/ERROR_CODES.md`.

## Safe fallback policy

For Pi hardware features:

- missing Picamera2 should report `PISD-CAM-001`
- camera open failure should report `PISD-CAM-002`
- missing GPIO should report `PISD-MOT-001`
- GPIO setup failure should report `PISD-MOT-002`
- fallback to simulation is allowed only when it is safe and clearly reported

## API response rule

All JSON endpoints must return a `code` field. This includes successful responses.

Example success:

```json
{"ok": true, "code": "PISD-OK-000", "message": "Motor config loaded."}
```

Example failure:

```json
{"ok": false, "code": "PISD-API-001", "message": "Request body was not valid JSON."}
```

## Testing rule

Any new service or API endpoint should add or update a script under `scripts/` that verifies:

- import path
- success JSON has `code`
- failure JSON has the expected non-OK code
- service status exposes `last_error_code` and `recent_errors`

Patch notes must state which error/reporting checks actually ran.

## Camera colour pipeline rule

For browser preview or saved visual evidence, prefer the Picamera2 request/PIL path when the backend is Picamera2. Raw arrays are still allowed for computer vision, but future code must state the expected channel order and report failures with PiSD error codes.

Do not silently swap RGB/BGR channels. For the current OV5647 setup, `03_request_awb_off_lock` is the visual reference/default and `91_array_rgb` is the raw array/CV reference. If a future camera module adds a new format or colour conversion path, expose the selected path in service status using fields similar to `last_capture_source` and `last_array_color_order`.
