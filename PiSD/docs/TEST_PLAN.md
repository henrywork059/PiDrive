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
- `03_request_awb_off_lock.jpg` should be treated as the main preview/training baseline

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

The visual camera path should use `capture_source=request`, with `03_request_awb_off_lock` selected as the current default after colour comparison. Raw array tests are optional; when needed, use `array_color_order=rgb` first because `91_array_rgb` was confirmed correct on the OV5647 setup.

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


## Front page and tab navigation test (0.2.6)

Run:

```bash
python3 scripts/test_front_page_tabs.py
```

Expected examples:

```text
OK   PISD-OK-000   front_page.route.root - / front page loaded
OK   PISD-OK-000   front_page.route.settings - /settings tab loaded
OK   PISD-OK-000   front_page.back_links - all tabs include Back to Front Page
```

Manual browser check:

1. Open `http://<pi-ip>:5050/`.
2. Click **Settings** and confirm `/settings` loads.
3. Click **Back to Front Page**.
4. Click **Testing** and confirm `/testing` loads.
5. Confirm `/dashboard` and `/panel-testing` also include **Back to Front Page**.

## Live frame FPS validation

Patch `0.2.7` adds FPS-specific checks for the camera preview pipeline.

Direct service test:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_camera_fps.py --hardware --seconds 5 --fps 30 --capture-source array
```

Local HTTP/MJPEG test, with server already running:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then in another terminal:

```bash
python3 scripts/test_live_frame_fps.py --base-url http://127.0.0.1:5050 --seconds 5 --mode mjpeg --apply-fast-preview
```

Testing GUI browser test:

1. Open `/testing`.
2. Use **Apply fast preview preset**.
3. Click **Start camera + live**.
4. Click **Run max FPS test**.

Expected OK lines use `PISD-OK-000`. FPS test failures use `PISD-TEST-017`.

## Panel presentation settings validation added in 0.2.8

Use this test after applying the 0.2.8 patch:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

With Flask available, run:

```bash
python3 scripts/test_panel_presentation_page.py
```

Expected OK lines include:

```text
OK   PISD-OK-000   panel_presentation.file.template - pisd/web/templates/panel_presentation.html exists
OK   PISD-OK-000   panel_presentation.source_contract - panel presentation page includes controls, save/apply/export/import, and global style application
OK   PISD-OK-000   panel_presentation.global_includes - shared panel presentation CSS/JS is included on all GUI pages
```

The `/panel-testing` page should remain available and separate.

## 0.2.9 manual drive and settings validation

After applying `PiSD_0_2_9_patch`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

On the Pi with Flask installed, start the server:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/
```

Checks:

- front page includes Manual Drive, Settings, Testing, Dashboard, Panel presentation, and Panel testing.
- `/manual-drive` loads and shows camera preview, running status, manual pad, speed/steer sliders, and STOP.
- manual movement buttons are locked until the safety checkbox is enabled.
- STOP is always available.
- `/settings` restores saved form values and applies runtime settings through the API.
- `/panel-presentation` auto-saves panel style choices and applies them across all tabs.

## PiSD 0.2.10 persistent settings and manual-drive UI checks

Run static and local settings checks:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

With the server running, check settings API persistence:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
python3 scripts/test_settings_persistence.py --base-url http://127.0.0.1:5050
```

Expected lines include:

```text
OK   PISD-OK-000   api.settings.get - settings endpoint loaded
OK   PISD-OK-000   api.settings.apply - settings saved and applied
OK   PISD-SET-003  api.settings.bad_payload - bad settings rejected
```

Manual drive visual checks:

1. Open `/settings`, change panel style values, click **Save and apply**.
2. Open `/manual-drive`, `/testing`, `/dashboard`, `/panel-testing`, and `/panel-presentation`.
3. Confirm panel density, radius, preview fit/aspect, button scale, and console height follow the saved settings.
4. In `/manual-drive`, confirm the status strip is short, the log is hidden until **Show action log** is clicked, and the drag pad sends no motor command unless armed.
5. With wheels lifted, arm the drag pad, drag gently, release, and confirm release sends STOP.

## PiSD 0.3.1 adaptive layout checks

After applying `PiSD_0_3_1_patch`, run the static/source checks first:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Then start the server and visually check the pages on the Pi browser:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/manual-drive
http://<pi-ip>:5050/panel-presentation
http://<pi-ip>:5050/settings
```

Expected manual-drive presentation:

- On PC/iPad width, the compact Status panel appears above the Preview panel.
- The Preview panel uses available screen height and should show the full frame without unnecessary scrolling on most PC/iPad screens.
- The drag pad remains beside the preview on wide/iPad landscape layouts and stacks below on small phone screens.
- The log stays hidden until expanded.

Expected panel-presentation/settings behaviour:

- Horizontal/vertical role weight controls are visible.
- Saving presentation settings applies across all pages through the backend settings API.
- Phone layouts still collapse panels to one column.


## PiSD 0.3.3 Manual Drive layout recovery checks

After applying `PiSD_0_3_3_patch`, run the static/source checks first:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Then start the server and visually check Manual Drive on a PC or iPad-sized screen:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/manual-drive
```

Expected Manual Drive layout:

- Status panel appears at the top of the main page area.
- Camera Preview panel appears directly under the Status panel.
- Manual Control drag pad appears in the right-side control column where the misplaced camera panel previously appeared.
- Emergency Stop appears under Manual Control.
- The preview should use the left/main content width and should not force the user to scroll past large empty space before seeing the control pad.
- The action log remains hidden until opened.

This is a presentation-only check. The patch does not change motor output, camera settings, API endpoints, or saved settings format.

## Presentation/layout regression checks added in 0.3.4

Before building any new GUI page or panel style patch, run:

```bash
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

These checks confirm that all templates use versioned static assets, the final shared design-system CSS is loaded last, the presentation registry exists, and Manual Drive keeps the required status -> camera preview -> controls layout contract.

## PiSD 0.3.5 recording and manual-drive layout checks

Run these after applying the 0.3.5 patch:

```bash
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

On the Pi, start the server and test the Manual Drive page:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/manual-drive
```

Check:

- status panel is top-left
- camera panel is directly under the status panel
- manual drag pad is in the right control column
- drag pad ball follows the pointer position
- speed slider can reach `1.0`
- `Snapshot` creates one saved frame and JSONL record
- `Record` starts/stops a session in `recordings/YYYY-MM-DD/...`
- `records.jsonl` contains camera settings, steering, throttle, motor output, bias, and tuning data for every saved frame

## PiSD 0.3.6 recording/layout safety checks

After applying `PiSD_0_3_6_patch`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_recording_service.py
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Manual browser checks:

1. Open `/manual-drive`.
2. Confirm the camera panel stays under the compact status panel and the drag pad stays in the control column.
3. Confirm the speed slider max is not 1.0 and the Settings page shows motor left/right max speed up to `1.0`.
4. Press `Snapshot` and confirm a visible capture notice appears.
5. Start `Record` and confirm the red recording indicator appears.
6. Stop recording and confirm the indicator returns to `REC off`.

Folder expectations:

- Continuous recordings: one folder per recording session under `recordings/YYYY-MM-DD/`.
- Single manual captures: all same-day captures under `recordings/single_captures/YYYY-MM-DD/`.

## PiSD 0.3.7 responsive layout checks

After applying `PiSD_0_3_7_patch`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_responsive_layout_contract.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Expected simple result style:

```text
OK   PISD-OK-000   responsive_layout.source_contract - shared responsive layout contract passed
```

Then start the server and visually check:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/manual-drive
http://<pi-ip>:5050/settings
http://<pi-ip>:5050/testing
http://<pi-ip>:5050/dashboard
http://<pi-ip>:5050/panel-presentation
http://<pi-ip>:5050/panel-testing
```

Manual Drive layout must be:

```text
status  status
preview drive
preview stop
log     log
```

On phone/portrait it must stack:

```text
status
preview
drive
stop
log
```

## PiSD 0.3.8 manual speed and recording-library checks

After applying this patch, check that the Manual Drive page allows full normalized range:

```text
Manual speed slider max = 1.0
Manual Drive has no steer-strength slider; drag-pad X directly maps to steering X
Motor left/right max speed settings can be set to 1.0
```

Run the safe local tests:

```bash
python3 scripts/test_recording_service.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
```

On the Pi browser:

1. Open `/manual-drive`.
2. Capture a single frame.
3. Confirm the `Records & snaps` panel lists a snapshot folder.
4. Start and stop a recording.
5. Confirm a recording folder appears.
6. Select a recording folder and click `Download zip`.
7. Select a snapshot folder and click `Download zip`.
8. Select an old/unneeded folder and click `Delete selected`.
9. Confirm active recording folders cannot be deleted until recording is stopped.

## PiSD 0.3.9 manual controls and top-bar button checks

After applying `PiSD_0_3_9_patch`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

On the Pi browser, hard refresh `/manual-drive` and check:

1. Manual Drive has no `Steer strength` slider; drag-pad X directly maps to steering X.
2. `/settings` has no `Steer strength` control; legacy `steer_strength` is ignored by settings normalisation.
3. `Start live` starts the camera service and switches the preview to `/video_feed` with one click.
4. Press `s` in Manual Drive to save a snapshot and press `r` to toggle recording.
5. Top-bar `Refresh status` visibly updates the compact status line without starting/restarting the camera preview.
6. Top-bar `STOP` sends `/api/control/stop`, recentres the drag pad, and updates the compact status line with the returned `PISD-*` code.

If Flask is installed in the environment, also run the non-static check:

```bash
python3 scripts/test_manual_drive_page.py
```

That test validates the Manual Drive page route plus the local API endpoints used by the key buttons.

## PiSD 0.3.10 manual-drive compact control checks

After applying `PiSD_0_3_10_patch`, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

On the Pi browser, hard refresh `/manual-drive` and check:

1. The drag-pad ball is noticeably smaller, about half the previous diameter.
2. The Preview panel no longer shows a `Snapshot view` button.
3. `Start live` starts the camera service and switches to `/video_feed`; there is no separate Start camera / Live stream pair.
4. Press `s` to capture a still frame; press `r` to start/stop recording.
5. The Status / Live signals panel shows compact current command values: intended steering/throttle.
6. The same panel also shows current motor output values: left/right motor output.
7. While dragging, `Cmd` updates immediately and `Out` updates after the `/api/control/manual` response.
8. Pressing `STOP` returns both `Cmd` and `Out` to zero.

Expected compact status fields include:

```text
HW | Cam | Motor | FPS | Rec | Cmd | Out
```
