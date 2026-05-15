# PATCH NOTES - PiSD 0.2.2

## Request summary

User requested more testing before moving from the temporary testing-server GUI toward the actual main server GUI, so that settings and API calling can be checked more smoothly.

## Cause / context

`PiSD_0_2_1` added the first temporary testing GUI. It exposed the main camera, motor, settings, STOP, custom API, and error-code calls in the browser, but the validation layer only checked that the page and manifest loaded.

Before building the real control GUI, the testing GUI should be checked more thoroughly:

- template/CSS/JS files must exist and contain the expected controls
- browser-facing API routes must remain wired
- static files must load through Flask
- the manifest must list required endpoints
- motor safety behaviour must remain locked by default
- bad inputs must return corresponding `PISD-*` codes

## Files changed

Changed:

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/static/css/testing_server.css`
- `PiSD/pisd/web/static/js/testing_server.js`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/README.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/TESTING_SERVER_GUI.md`
- `PiSD/docs/TEST_PLAN.md`

Added:

- `PiSD/scripts/test_testing_server_gui.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_2.md`

## Behaviour changed

### Browser safe smoke test

The testing GUI now includes a `Run safe smoke test` button.

The browser-side smoke test calls safe API routes in sequence:

- `GET /api/status`
- `GET /api/test-gui/manifest`
- `POST /api/camera/start`
- `GET /api/camera/config`
- `GET /api/camera/frame.jpg`
- `POST /api/camera/apply` with the known-good request/RGB-safe settings
- `GET /api/motor/config`
- `POST /api/motor/apply`
- `POST /api/motor/test-channel` without arming motor output
- `POST /api/control/stop`

The smoke test does not send `enable_motor_output: true`. In simulation mode, the motor-channel check may complete safely with `PISD-OK-000`. In real hardware mode, the expected safe result is a refusal with `PISD-MOT-008`.

### Stronger standard validation

`run_standard_validation.py` now also checks:

- testing GUI template/CSS/JS files exist
- testing GUI source includes required IDs, API calls, smoke-test controls, and safety-code references
- `/` loads the testing page
- `/testing` loads the testing page
- testing GUI static CSS and JS load through Flask
- `/api/test-gui/manifest` contains required API paths and known-good camera references
- invalid motor-channel side returns `PISD-MOT-007`
- unknown route returns `PISD-API-003`

Added option:

```bash
python3 scripts/run_standard_validation.py --skip-gui
```

### Focused testing-GUI script

Added:

```bash
python3 scripts/test_testing_server_gui.py
```

It prints simple OK/FAIL lines with PiSD codes and writes:

```text
test_outputs/testing_server_gui/summary.json
```

Static-only mode for packaging or PCs without Flask:

```bash
python3 scripts/test_testing_server_gui.py --static-only
```

## Error reporting

Added:

- `PISD-TEST-010` — testing server GUI template, CSS, JS, or static asset contract failed validation.
- `PISD-TEST-011` — testing server GUI API contract or browser smoke-test sequence failed validation.

Existing relevant codes preserved:

- `PISD-TEST-009` — testing GUI route/manifest route failed validation.
- `PISD-MOT-007` — invalid motor-channel test input.
- `PISD-MOT-008` — real motor-channel test refused because output was not armed.
- `PISD-API-003` — unknown route.

## Safety behaviour

Real motor output remains locked by default.

The new browser smoke test deliberately does not arm real motor output. It checks safe API wiring and STOP behaviour, not physical driving.

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile scripts/run_standard_validation.py scripts/test_testing_server_gui.py scripts/test_api_endpoints.py pisd/core/errors.py`
- `python3 scripts/test_testing_server_gui.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`
- checked patch-only zip contents
- confirmed no `__pycache__` folders are included
- confirmed no duplicate `requirement.txt` was restored

## Not verified here

- Full Flask route execution, because Flask is not installed in this packaging environment.
- Real Raspberry Pi camera hardware.
- Real GPIO/motor output.
- Browser rendering on the Pi screen.

Run these on the Pi after applying the patch:

```bash
python3 scripts/test_testing_server_gui.py
python3 scripts/run_standard_validation.py --hardware
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then open the testing GUI and press:

```text
Run safe smoke test
```

## Known limits / next steps

- This patch still does not add persistent settings.
- This patch is still the temporary testing GUI, not the final driving GUI.
- After the tests pass on the Pi, the next patch can add settings persistence or begin the final main GUI layout.
