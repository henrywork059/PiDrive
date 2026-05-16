# PiSD 0.2.5 Patch Notes — Main Dashboard GUI Shell

## Request summary

Create the next PiSD patch after the panel API contract work: the first actual GUI server shell, while keeping the testing pages separate.

The user specifically wanted the GUI testing work to happen before the final/actual GUI, and after the testing-server and panel-contract work was accepted, this patch starts the actual dashboard shell without adding advanced layout persistence, recording, AI model, or lane runtime features yet.

## Cause / design reason

Before this patch, `/` and `/testing` both served the temporary API/settings testing GUI. That was useful for service validation, but it was not a clean starting point for the actual control dashboard.

The project now needs a separate real dashboard route so future GUI work can build forward cleanly while retaining:

- `/testing` for API/settings testing
- `/panel-testing` for panel layout/API contract testing
- existing camera, motor, and error-code APIs

## Files changed

```text
PiSD/pisd/__init__.py
PiSD/pisd/app.py
PiSD/pisd/core/errors.py
PiSD/pisd/web/templates/main_dashboard.html
PiSD/pisd/web/static/css/main_dashboard.css
PiSD/pisd/web/static/js/main_dashboard.js
PiSD/scripts/test_main_dashboard.py
PiSD/scripts/test_api_endpoints.py
PiSD/scripts/test_testing_server_gui.py
PiSD/scripts/run_standard_validation.py
PiSD/docs/GUI_FUNCTION_SPEC.md
PiSD/docs/TEST_PLAN.md
PiSD/docs/TESTING_SERVER_GUI.md
PiSD/docs/ERROR_CODES.md
PiSD/README.md
PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_5.md
```

## Behaviour changed

### Main route now points to the actual dashboard shell

```text
/               actual main dashboard shell
/testing        temporary API/settings testing GUI
/panel-testing  panel layout/API contract testing lab
```

### New dashboard files

Added:

```text
PiSD/pisd/web/templates/main_dashboard.html
PiSD/pisd/web/static/css/main_dashboard.css
PiSD/pisd/web/static/js/main_dashboard.js
```

The first dashboard shell includes:

- System Status
- Camera Preview
- Manual Drive
- Motor Channel Calibration
- Safety Stop
- Error Monitor
- Action Log

### Safety behaviour

Manual-drive and motor-channel controls are locked by default in the dashboard.

They only enable after the user ticks:

```text
I confirm the wheels are lifted and motor output is safe to test.
```

STOP controls remain available at all times.

### Testing pages preserved

The existing `/testing` API/settings test page and `/panel-testing` lab remain available.

### Validation added

Added:

```text
PiSD/scripts/test_main_dashboard.py
```

This checks:

- dashboard files exist
- required panels exist
- safety lock tokens exist
- STOP buttons exist
- root `/` loads the main dashboard
- `/testing` remains available
- `/panel-testing` remains available
- main dashboard CSS/JS static files load
- STOP API remains safe

### Error codes added

Added:

```text
PISD-TEST-015
```

Used for main-dashboard template, asset, route, or safe API contract validation failures.

## Verification performed

Local verification performed in this packaging environment:

```text
python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_testing_server_gui.py --static-only
python3 scripts/test_panel_testing_page.py --static-only
python3 scripts/test_panel_api_contracts.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Also checked patch packaging:

- patch zip contains changed/new files only
- no `__pycache__`
- no `test_outputs`
- no duplicate `requirement.txt`
- existing PiServer files were not touched

## Not verified here

Not verified in this local environment:

- browser interaction on the Raspberry Pi
- real Picamera2 hardware through the new dashboard buttons
- real motor output through the new dashboard buttons
- Flask route execution if Flask is missing on the packaging machine

The Pi-side validation command after applying this patch is:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_main_dashboard.py
python3 scripts/run_standard_validation.py --hardware --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then open:

```text
http://<pi-ip>:5050/
```

## Known limits / next steps

This is intentionally a dashboard shell. It does not yet include:

- draggable/resizable panel persistence
- full camera settings editor on the main dashboard
- full motor settings editor on the main dashboard
- dataset recording
- model/lane runtime integration
- final styling polish

Recommended next patch:

```text
PiSD_0_2_6_patch — main dashboard camera/motor settings panels with safe apply/reset behaviour
```
