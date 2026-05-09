# PiSD 0.0.5 Patch Notes — Full camera setting control/test coverage

## Request summary

User requested that the PiSD camera service and test code should be able to control and test all practical camera settings, including size, exposure, white balance, buffer, quality, and related camera behaviour. User also reported that colour diagnostic outputs `03` and `05` were wrong.

## Cause / context

PiSD 0.0.4 added a safer request/PIL camera path and a colour diagnostic script, but camera settings were still only partly exposed through command-line tests and defaults. The old colour diagnostic script always produced array-path test frames. On the tested OV5647 camera, array-path outputs `03_array_auto` and `05_array_bgr_interpretation` were reported wrong, confirming that raw array/OpenCV interpretation should not be the default visual reference.

## Files changed

- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/__init__.py`
- `PiSD/config/defaults.json`
- `PiSD/scripts/test_camera_service.py`
- `PiSD/scripts/diagnose_camera_color.py`
- `PiSD/scripts/dump_camera_capabilities.py`
- `PiSD/scripts/test_camera_settings_matrix.py`
- `PiSD/docs/CAMERA_SETTINGS.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_5.md`

## Behaviour changed

### Camera service

The camera service now exposes these setting groups:

- size: `width`, `height`
- frame rate: `fps`, applied through `FrameDurationLimits`
- format: `format`
- JPEG quality: `preview_quality`
- capture path: `capture_source`
- raw array interpretation: `array_color_order`
- buffer and queue: `buffer_count`, `queue`
- image transform: `hflip`, `vflip`
- exposure: `auto_exposure`, `exposure_us`, `analogue_gain`, `exposure_compensation`
- auto-exposure modes: `ae_metering_mode`, `ae_exposure_mode`, `ae_constraint_mode`
- white balance: `auto_white_balance`, `awb_mode`, `colour_gains_red`, `colour_gains_blue`, `awb_settle_seconds`
- image controls: `brightness`, `contrast`, `saturation`, `sharpness`
- noise reduction: `noise_reduction_mode`
- optional crop: `scaler_crop`

### Colour path decision

- `capture_source=request` remains the default and recommended visual preview path.
- Raw `array` modes are now marked diagnostic/CV-only.
- `diagnose_camera_color.py` no longer includes array diagnostics by default.
- Array tests can still be run using `--include-array-diagnostics`.

### API

Added:

- `GET /api/camera/capabilities`

The existing `POST /api/camera/apply` can now accept the expanded camera settings.

### Testing scripts

Added:

- `scripts/dump_camera_capabilities.py`
- `scripts/test_camera_settings_matrix.py`

Expanded:

- `scripts/test_camera_service.py`
- `scripts/diagnose_camera_color.py`

## Error reporting

Added error codes:

- `PISD-CAM-009` — invalid, ignored, or partly applicable camera setting
- `PISD-CAM-010` — camera capability query failed
- `PISD-TEST-006` — camera settings matrix failed

Unsupported controls should report warnings/errors instead of crashing.

## Verification actually performed

Performed locally in the packaging environment:

- Python compile check for changed service, app, core, and scripts
- `python3 PiSD.py --status-only`
- `python3 scripts/test_camera_service.py`
- `python3 scripts/test_camera_settings_matrix.py`
- `python3 scripts/dump_camera_capabilities.py`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/check_service_imports.py` returned successfully; it correctly reported Flask app creation as unavailable because Flask is not installed in this packaging environment
- zip structure check
- confirmed only `requirements.txt` exists; no duplicate `requirement.txt`

## Not verified here

- Flask API endpoint smoke test in this packaging environment, because Flask is not installed locally
- Real OV5647/Picamera2 hardware setting effects
- Real motor hardware
- Whether every libcamera enum is supported on the user's installed Raspberry Pi OS/libcamera build

The patch is designed to report unsupported enum/control failures with PiSD error codes instead of crashing.

## Known limits / next steps

- The request/PIL path is the visual reference for GUI preview.
- Raw array mode still needs separate colour-order calibration before it should be trusted for display.
- Future GUI work should read/write these same camera settings instead of creating separate UI-only values.
