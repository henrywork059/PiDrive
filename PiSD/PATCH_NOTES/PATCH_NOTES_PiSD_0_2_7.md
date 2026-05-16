# PiSD 0.2.7 Patch Notes — Live Frame FPS Pipeline Testing

## Request summary

Improve maximum running live-preview FPS before building more of the main GUI server, and include max-FPS testing in the testing page.

## Root cause / design issue

The existing GUI preview path used repeated snapshot refreshes from `/api/camera/frame.jpg`, which can artificially limit displayed FPS and adds browser polling overhead. The backend already cached JPEG frames, but `/video_feed` still used a heavier status lookup per loop and did not wait efficiently for new frames.

## Files changed / added

Changed:

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/core/panel_contracts.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/css/testing_server.css`
- `PiSD/pisd/web/static/js/testing_server.js`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_testing_server_gui.py`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/docs/TESTING_SERVER_GUI.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/README.md`

Added:

- `PiSD/scripts/test_camera_fps.py`
- `PiSD/scripts/test_live_frame_fps.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_7.md`

## Behaviour changed

- Added efficient frame wait/notify support in `CameraService`.
- Added lightweight `get_jpeg_frame_info()` and `wait_for_jpeg_frame()` methods so `/video_feed` does not need to call full `status()` for every frame.
- Added camera FPS metrics:
  - `target_fps`
  - `measured_capture_fps`
  - `last_capture_loop_ms`
  - `average_capture_loop_ms`
  - `last_encode_ms`
  - `average_encode_ms`
  - `last_frame_bytes`
  - `frames_dropped_or_empty`
- Added `GET /api/camera/fps-stats`.
- Updated `/video_feed` to wait for a new frame instead of spinning or repeatedly building full status payloads.
- Updated the testing page with a **Live FPS pipeline test** panel.
- Added a fast preview preset using the confirmed RGB array path.
- Updated the main dashboard preview button to use `/video_feed` for live preview.
- Kept `/api/camera/frame.jpg` for snapshots and API smoke tests.
- Added error code `PISD-TEST-017` for FPS validation failures.

## Verification actually performed

Performed locally in this packaging environment:

- `python3 -m compileall -q PiSD.py pisd scripts`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_testing_server_gui.py --static-only`
- `python3 scripts/test_main_dashboard.py --static-only`
- `python3 scripts/test_panel_api_contracts.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`
- `python3 scripts/test_camera_fps.py --seconds 2 --fps 20 --capture-source array`

The direct simulation FPS test measured about 20 FPS with target 20 FPS in this environment.

## Not verified here

- Real Raspberry Pi OV5647 hardware FPS.
- Browser-rendered MJPEG FPS on the Pi.
- Flask route execution in this packaging environment, because Flask is not installed here.

## Recommended Pi-side tests

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_camera_fps.py --hardware --seconds 5 --fps 30 --capture-source array
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

In a second terminal:

```bash
python3 scripts/test_live_frame_fps.py --base-url http://127.0.0.1:5050 --seconds 5 --mode mjpeg --apply-fast-preview
```

Then open:

```text
http://<pi-ip>:5050/testing
```

Use the **Live FPS pipeline test** panel.

## Known limits / next steps

- Fast preview mode uses `capture_source=array` and `array_color_order=rgb`, which was previously confirmed as correct for this OV5647 setup.
- Request/PIL remains the trusted visual reference path.
- Real max FPS still depends on camera resolution, exposure time, JPEG quality, CPU load, browser/device, and network conditions.
