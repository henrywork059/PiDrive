# PATCH NOTES - PiSD 0.2.1

## Request summary

User requested the next GUI patch, but clarified that this should not yet be the actual final GUI server. The patch should first add a testing server GUI that verifies settings and API calls before building the real/main control GUI.

## Cause / context

`PiSD_0_2_0` is the stable v2 backend baseline. It already contains tested camera service, motor service, one-by-one motor channel tests, local APIs, and the standard OK/FAIL validation script.

Before a full GUI is built, the project needs a browser page that exercises those APIs directly so camera settings, motor settings, safety refusal, and response/error codes can be tested from the Pi browser or another device on the LAN.

## Files changed

Changed:

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/README.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/TEST_PLAN.md`

Added:

- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/static/css/testing_server.css`
- `PiSD/pisd/web/static/js/testing_server.js`
- `PiSD/docs/TESTING_SERVER_GUI.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_1.md`

## Behaviour changed

### Testing server GUI

Added a temporary API/settings test page at:

```text
/
/testing
```

The page includes:

- camera preview
- camera start/stop/frame refresh buttons
- camera config and capabilities API calls
- camera settings apply form
- motor settings apply form
- one-by-one motor channel test form
- custom API caller
- response/status/error-code panels
- emergency STOP button

This replaces the previous embedded one-page HTML string in `pisd/app.py` with real template/static files under `pisd/web/`.

### New API manifest endpoint

Added:

```text
GET /api/test-gui/manifest
```

The manifest lists the important testing endpoints and the known-good camera colour references:

- visual path: `01_request_awb_auto`
- raw array/CV path: `91_array_rgb_confirmed_correct`
- default `capture_source=request`
- default `array_color_order=rgb`

### Safety behaviour preserved

Real motor channel output remains locked unless the request includes:

```json
{"enable_motor_output": true}
```

If the server is hardware-enabled and the user does not arm motor output, `/api/motor/test-channel` still returns:

```text
PISD-MOT-008
```

The testing GUI sends this flag only when the user checks the wheel-lifted arming checkbox.

### Validation updated

`run_standard_validation.py` now checks:

- `GET /testing`
- `GET /api/test-gui/manifest`

Expected lines:

```text
OK   PISD-OK-000   api.testing_gui.page - testing GUI page loaded
OK   PISD-OK-000   api.testing_gui.manifest - testing GUI manifest loaded
```

`test_api_endpoints.py` also checks the testing GUI page and manifest.

## Error reporting

Added:

```text
PISD-TEST-009
```

Meaning: testing server GUI route or manifest failed local validation.

No new motor/camera runtime error codes were needed. The page displays existing `PISD-*` response codes returned by the API.

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`
- checked the testing GUI template/static files exist under `pisd/web/`
- patch-only zip structure check
- confirmed only changed/new files are included
- confirmed `requirements.txt` remains the only dependency file and `requirement.txt` was not restored

## Not verified here

- Real Raspberry Pi camera hardware, because this packaging environment has no Pi camera attached.
- Real motor output, because this packaging environment has no GPIO/motor hardware.
- Flask route execution in this packaging environment, because Flask is not installed here. The route code compiles and is intended to be verified on the Pi where Flask is already installed.
- Browser rendering on the Pi screen.

## Known limits / next steps

- This is intentionally a testing GUI, not the final driving GUI.
- It does not save persistent settings yet.
- It does not include dockable panels, recording, AI model loading, lane detection, or dataset capture.
- Next patch after user testing should either fix any testing GUI/API issues or add persistence for camera/motor settings before moving to the final GUI design.
