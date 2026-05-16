# PiSD Test Plan


## Standard validation script

Preferred quick test before building or changing the main server/GUI:

```bash
python3 scripts/run_standard_validation.py
```

Expected successful output uses one line per function:

```text
OK   PISD-OK-000   config.load_defaults - defaults loaded
OK   PISD-OK-000   core.error_reporting_schema - error payloads include PiSD codes
OK   PISD-OK-000   services.import_and_status - camera and motor services imported
OK   PISD-OK-000   main_dashboard.static_files - main dashboard template/CSS/JS files exist
OK   PISD-OK-000   main_dashboard.source_contract - main dashboard source contains required panels, safety lock, STOP actions, and API calls
OK   PISD-OK-000   gui.static_files - testing GUI template/CSS/JS files exist
OK   PISD-OK-000   gui.source_contract - testing GUI source contains required IDs, API calls, safety checks, and code display
OK   PISD-OK-000   camera.service_frame - frame captured (12345 bytes)
OK   PISD-OK-000   camera.apply_settings - camera settings applied and frame captured
OK   PISD-OK-000   motor.service_channels - left/right direction tests completed and stopped
OK   PISD-OK-000   api.main_dashboard.root_page - / main dashboard page loaded
OK   PISD-OK-000   api.main_dashboard.static_css - /testing/static/css/main_dashboard.css asset loaded
OK   PISD-OK-000   api.main_dashboard.static_js - /testing/static/js/main_dashboard.js asset loaded
OK   PISD-OK-000   api.main_dashboard.stop_safe - dashboard STOP API call returned OK
OK   PISD-OK-000   api.testing_gui.page - /testing GUI page loaded
OK   PISD-OK-000   api.testing_gui.static_css - /testing/static/css/testing_server.css asset loaded
OK   PISD-OK-000   api.testing_gui.static_js - /testing/static/js/testing_server.js asset loaded
OK   PISD-OK-000   api.testing_gui.manifest_contract - testing GUI manifest includes required endpoints and known-good camera references
OK   PISD-MOT-007  api.motor.test_channel_invalid_side - invalid motor side returned PISD-MOT-007
OK   PISD-API-003  api.not_found_error_code - unknown route returned PISD-API-003
OK   PISD-OK-000   api.status - status endpoint returned OK
OK   PISD-OK-000   api.camera.start - camera start endpoint OK
OK   PISD-OK-000   api.camera.frame - camera frame endpoint returned JPEG (12345 bytes)
OK   PISD-OK-000   api.motor.config - motor config endpoint OK
OK   PISD-OK-000   api.motor.test_channel - motor channel API tests completed
OK   PISD-OK-000   api.control.stop - stop endpoint reset outputs
OK   PISD-API-001  api.invalid_json_error_code - invalid JSON returned PISD-API-001
OK   PISD-OK-000   summary - passed=13 failed=0 output=.../summary.json
```

The invalid-JSON line is marked `OK` because the correct behaviour is to reject bad input with `PISD-API-001` instead of crashing.

Real camera/GPIO adapter check, without moving motors:

```bash
python3 scripts/run_standard_validation.py --hardware
```

When `--hardware` is used without motor arming, the motor channel API should refuse live movement safely:

```text
OK   PISD-MOT-008  api.motor.test_channel_safety_refusal - unarmed real motor test refused safely
```

Real camera and real one-by-one motor-output check. Use only with wheels lifted:

```bash
python3 scripts/run_standard_validation.py --hardware --enable-motor-output
```

The script writes a full machine-readable report to:

```text
test_outputs/standard_validation/summary.json
```

Useful options:

```bash
python3 scripts/run_standard_validation.py --skip-api
python3 scripts/run_standard_validation.py --skip-camera
python3 scripts/run_standard_validation.py --skip-motor
python3 scripts/run_standard_validation.py --hardware --enable-motor-output --motor-speed 0.10 --motor-duration 0.20
```

`PISD-TEST-008` means at least one standard validation item failed. Read the failed line and `summary.json` for the exact function and code.



## Main dashboard GUI shell check

`PiSD_0_2_5` makes `/` the actual dashboard shell. The temporary testing page remains at `/testing`.

Focused validation:

```bash
python3 scripts/test_main_dashboard.py
```

Expected OK examples:

```text
OK   PISD-OK-000   main_dashboard.file.template - pisd/web/templates/main_dashboard.html exists
OK   PISD-OK-000   main_dashboard.source_contract - main dashboard source includes required panels, safety lock, STOP actions, and API calls
OK   PISD-OK-000   main_dashboard.route.root - / loads the actual main dashboard
OK   PISD-OK-000   main_dashboard.route.testing_still_available - /testing remains available
OK   PISD-OK-000   main_dashboard.route.panel_testing_still_available - /panel-testing remains available
OK   PISD-OK-000   main_dashboard.api.stop_safe - STOP API remains safe from dashboard test
```

The script does not arm or move motors. The dashboard itself keeps movement controls disabled until the safety checkbox is selected.

Focused testing-GUI validation:

```bash
python3 scripts/test_testing_server_gui.py
```

Expected OK examples:

```text
OK   PISD-OK-000   gui.file.template - pisd/web/templates/testing_server.html exists
OK   PISD-OK-000   gui.source_contract - GUI source includes required controls, smoke test, API paths, and safety code
OK   PISD-OK-000   api.testing_gui.root - / loaded
OK   PISD-OK-000   api.static.js - /testing/static/js/testing_server.js loaded
OK   PISD-MOT-007  api.motor.invalid_channel_code - invalid motor channel returns PISD-MOT-007
OK   PISD-API-003  api.not_found_code - unknown route returns PISD-API-003
```

On a packaging PC without Flask, use static-only mode:

```bash
python3 scripts/test_testing_server_gui.py --static-only
```

## Testing server GUI check

Start the server:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/          # actual main dashboard shell
http://<pi-ip>:5050/testing    # temporary API/settings tester
```

Expected for `/testing`:

- page title says `PiSD Testing Server GUI`
- global code starts as `PISD-OK-000`
- camera service buttons call real camera APIs
- camera settings form calls `/api/camera/apply`
- motor settings form calls `/api/motor/apply` without moving wheels
- motor channel test calls `/api/motor/test-channel`
- unarmed real motor output returns `PISD-MOT-008`
- STOP calls `/api/control/stop`
- custom API caller can call `/api/status` and show JSON output
- `Run safe smoke test` completes status/manifest/camera/motor-safety/STOP checks without arming real motor output

Local no-network page validation:

```bash
python3 scripts/run_standard_validation.py --skip-camera --skip-motor
```

Expected OK lines:

```text
OK   PISD-OK-000   api.main_dashboard.root_page - / main dashboard page loaded
OK   PISD-OK-000   api.main_dashboard.static_css - /testing/static/css/main_dashboard.css asset loaded
OK   PISD-OK-000   api.main_dashboard.static_js - /testing/static/js/main_dashboard.js asset loaded
OK   PISD-OK-000   api.main_dashboard.stop_safe - dashboard STOP API call returned OK
OK   PISD-OK-000   api.testing_gui.page - /testing GUI page loaded
OK   PISD-OK-000   api.testing_gui.static_css - /testing/static/css/testing_server.css asset loaded
OK   PISD-OK-000   api.testing_gui.static_js - /testing/static/js/testing_server.js asset loaded
OK   PISD-OK-000   api.testing_gui.manifest_contract - testing GUI manifest includes required endpoints and known-good camera references
OK   PISD-MOT-007  api.motor.test_channel_invalid_side - invalid motor side returned PISD-MOT-007
OK   PISD-API-003  api.not_found_error_code - unknown route returned PISD-API-003
```

## Local checks

From inside `PiSD/`:

```bash
python -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py
python PiSD.py --status-only
python scripts/check_error_reporting.py
python scripts/check_service_imports.py
python scripts/test_api_endpoints.py
python scripts/test_camera_service.py
python scripts/test_motor_service.py
```

Expected in simulation mode:

- imports succeed
- error/reporting schema check succeeds
- default config loads
- Flask app factory creates the API app
- camera service starts and writes a JPEG under `test_outputs/`
- API test receives JPEG bytes from `/api/camera/frame.jpg`
- motor service maps steering/throttle into left/right outputs
- STOP resets left/right motor output to zero

## Package install check

```bash
python -m pip install -r requirements.txt
```

## Web smoke test

```bash
python PiSD.py
```

Open:

```text
http://127.0.0.1:5050
http://127.0.0.1:5050/api/status
```

Expected in simulation mode:

- web page loads
- status JSON returns and includes `code`, `last_error_code`, and `recent_errors` fields
- camera can start in simulation
- preview image changes over time
- steering/throttle sliders update motor simulation state
- STOP resets left/right motor output to zero

## API smoke test without network server

```bash
python scripts/test_api_endpoints.py
```

This uses Flask's local test client. It checks:

- `GET /api/status`
- `POST /api/camera/start`
- `GET /api/camera/frame.jpg`
- `GET /api/motor/config`
- `GET /api/errors`
- invalid JSON returns `PISD-API-001`
- `POST /api/control/manual`
- `POST /api/control/stop`
- `POST /api/camera/stop`

## Live HTTP API test

Start the server in one terminal:

```bash
python PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

In another terminal:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050
```

This verifies the actual HTTP route path to the running server. It does not move motors unless this extra flag is used:

```bash
python scripts/test_live_http_api.py --base-url http://127.0.0.1:5050 --enable-motor-output
```

## Raspberry Pi camera hardware test

Only run on the Pi with the camera connected and Picamera2 installed.

```bash
python scripts/test_camera_service.py --hardware
```

Expected:

- script prints `start_ok=True`
- status reports `backend: picamera2` if the real camera opened
- a JPEG is saved to `test_outputs/camera_service_frame.jpg`

If Picamera2 is unavailable or fails to open, the service should report the error and fall back to simulation rather than crashing.

## Raspberry Pi motor hardware test

Only run when the car is safe, wheels are lifted, and motor power is controlled.

Simulation-only mapping test:

```bash
python scripts/test_motor_service.py
```

Real GPIO output test:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output
```

Optional pin override example:

```bash
python scripts/test_motor_service.py --hardware --enable-motor-output --left-pins 17,27 --right-pins 22,23
```

Expected:

- status reports `adapter: rpigpio` when GPIO is available and real output is enabled
- each low-power command runs briefly
- final stop command resets outputs to zero
- script calls `motor.close()` before exit

## Error-code reporting check

This test does not require Flask or Raspberry Pi hardware:

```bash
python scripts/check_error_reporting.py
```

Expected:

- returns `code: PISD-OK-000`
- verifies `ok_payload` and `report_payload`
- verifies camera and motor status include `last_error_code` and `recent_errors`

## Verification rule

Patch notes must only claim tests that were actually run.

## Camera colour diagnostic test

Use this when the camera opens but the saved frame colour looks wrong.

```bash
python scripts/diagnose_camera_color.py --hardware
```

Optional extended check:

```bash
python scripts/diagnose_camera_color.py --hardware --include-rgb-format
```

Expected:

- files are saved under `test_outputs/camera_color/`
- `summary.json` records backend, capture source, colour path, metadata, and any PiSD error code
- `01_request_awb_auto.jpg` should be treated as the main preview baseline

Single-frame camera test with explicit preview path:

```bash
python scripts/test_camera_service.py --hardware --capture-source request
```

Raw array colour-order comparison:

```bash
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb --output test_outputs/array_rgb.jpg
python scripts/test_camera_service.py --hardware --capture-source array --array-color-order bgr --output test_outputs/array_bgr.jpg
```

Manual AWB lock test:

```bash
python scripts/test_camera_service.py --hardware --awb-off --output test_outputs/awb_off_lock.jpg
```

Manual colour gains example:

```bash
python scripts/test_camera_service.py --hardware --colour-gains 1.5,1.2 --output test_outputs/manual_colour_gains.jpg
```

Only keep manual gains if the result is visually better under the real lighting used by the car.

---

## PiSD 0.0.5 camera settings tests

The visual camera path should use `capture_source=request`, with `01_request_awb_auto` confirmed correct. Raw array tests are optional; when needed, use `array_color_order=rgb` first because `91_array_rgb` was confirmed correct on the OV5647 setup.

### Dump camera capabilities

```bash
python3 scripts/dump_camera_capabilities.py --hardware
```

### Test individual camera settings

```bash
python3 scripts/test_camera_service.py --hardware --capture-source request
python3 scripts/test_camera_service.py --hardware --width 640 --height 360 --fps 15 --preview-quality 80 --buffer-count 4 --no-queue
python3 scripts/test_camera_service.py --hardware --manual-exposure --exposure-us 8000 --analogue-gain 1.5
python3 scripts/test_camera_service.py --hardware --awb-mode daylight
python3 scripts/test_camera_service.py --hardware --awb-off --colour-gains 1.8,1.2
python3 scripts/test_camera_service.py --hardware --brightness 0.05 --contrast 1.2 --saturation 1.2 --sharpness 1.1
```

### Run the camera settings matrix

```bash
python3 scripts/test_camera_settings_matrix.py --hardware
```

Optional raw array diagnostics:

```bash
python3 scripts/test_camera_settings_matrix.py --hardware --include-array-diagnostics
python3 scripts/diagnose_camera_color.py --hardware --include-array-diagnostics
```


---

## PiSD 0.1.1 one-by-one motor channel tests

Simulation-only check:

```bash
python3 scripts/test_motor_channels.py
```

Real GPIO check with wheels lifted:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output
```

Recommended low-speed first run:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --speeds 0.10,0.15,0.20 --duration 0.30
```

Expected:

- left motor is tested by itself
- right motor is tested by itself
- each side tests raw `direction_1` and `direction_2`
- each direction tests the requested speed list
- every step automatically stops
- summary file is written to `test_outputs/motor_channels/summary.json`
- final code is `PISD-OK-000` unless a step failed

Live HTTP API single-channel check with server already running:

```bash
python3 scripts/test_live_http_api.py --base-url http://127.0.0.1:5050 --enable-motor-output
```

This now also calls `POST /api/motor/test-channel` before the existing manual control check.

## Panel testing GUI validation

After applying `PiSD_0_2_3`, run:

```bash
python3 scripts/test_panel_testing_page.py
```

Expected successful output includes:

```text
OK   PISD-OK-000   panel_gui.file.template - pisd/web/templates/panel_testing.html exists
OK   PISD-OK-000   panel_gui.source_contract - panel lab source includes panel registry, style controls, size controls, and responsive rules
OK   PISD-OK-000   panel_gui.route.page - /panel-testing loaded
OK   PISD-OK-000   panel_gui.manifest_contract - panel manifest lists planned final panels and style controls
```

Static-only packaging check:

```bash
python3 scripts/test_panel_testing_page.py --static-only
```

The standard validation script now also checks the panel testing GUI unless `--skip-gui` is used:

```bash
python3 scripts/run_standard_validation.py --skip-camera --skip-motor
```

---

## PiSD 0.2.4 panel API contract validation

After applying `PiSD_0_2_4_patch`, validate the panel API contracts before starting the final GUI server work.

Static/data-only contract check:

```bash
python3 scripts/test_panel_api_contracts.py --static-only
```

Full safe local API contract check:

```bash
python3 scripts/test_panel_api_contracts.py
```

Hardware-mode check without arming motors:

```bash
python3 scripts/test_panel_api_contracts.py --hardware
```

Expected output contains simple `OK`, `SKIP`, or `FAIL` lines with PiSD codes:

```text
OK   PISD-OK-000   panel_contract.registry - 12 panel contracts declared
OK   PISD-OK-000   panel_contract.fields - all panel contracts include required fields
OK   PISD-OK-000   panel.system_status.api - safe action returned expected code via HTTP 200
SKIP PISD-TEST-013 panel.recording.placeholder - future placeholder intentionally skipped
```

In the browser, open:

```text
http://<pi-ip>:5050/panel-testing
```

Use:

```text
Run structure checks
Run panel API checks
```

`Run panel API checks` must not arm real motor output. Motor-channel checks should either pass in simulation with `PISD-OK-000` or refuse safely in hardware mode with `PISD-MOT-008`.

The standard validation script also checks panel API contract data and the contract routes:

```bash
python3 scripts/run_standard_validation.py --hardware --skip-camera --skip-motor
```
