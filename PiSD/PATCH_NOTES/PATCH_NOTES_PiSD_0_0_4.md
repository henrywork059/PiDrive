# PATCH NOTES - PiSD 0.0.4

## Request summary

The real Picamera2 hardware test opened successfully on the Raspberry Pi, but the saved test frame colour looked wrong. The user asked for the issue to be handled within the PiSD service path.

## Observed evidence

The uploaded terminal log showed:

- Picamera2 detected an OV5647 camera through libcamera.
- `scripts/test_camera_service.py --hardware` returned `start_ok=True`.
- `backend` was `picamera2`.
- `hardware_enabled` was `true`.
- `last_error_code` was `PISD-OK-000`.
- The saved frame path was `test_outputs/camera_service_frame.jpg`.

This means the camera open/capture path was working, so the next likely problem area was colour handling, AWB/tuning, or RGB/BGR conversion.

## Likely cause

The previous PiSD camera preview path used:

1. `Picamera2.capture_array("main")`
2. local OpenCV/Pillow JPEG encoding

That raw-array path is useful for computer vision, but it can make visual preview colour debugging unreliable if the channel order is interpreted incorrectly. The existing PiServer reference had already moved toward a Picamera2 request/PIL image path for preview to better match Picamera2's own image conversion behaviour.

## Files changed

- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/__init__.py`
- `PiSD/config/defaults.json`
- `PiSD/scripts/test_camera_service.py`
- `PiSD/scripts/diagnose_camera_color.py`
- `PiSD/README.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/FUTURE_CODE_RULES.md`
- `PiSD/docs/DIRECTORY_GUIDE.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_4.md`

## Behaviour changed

### Camera preview path

Default camera config now uses:

```json
"capture_source": "request"
```

For Picamera2 hardware mode, this uses `capture_request()` and `request.make_image("main")` for the JPEG preview path. This is intended to avoid RGB/BGR channel-order mistakes in the saved/browser preview.

The raw array path remains available for future CV work:

```json
"capture_source": "array"
```

### Colour-order diagnostics

Added raw-array colour-order handling:

```json
"array_color_order": "auto"
```

Supported values:

- `auto`
- `bgr`
- `rgb`
- `bgra`
- `rgba`
- `swap_rb`
- `none`

### AWB / colour controls

Added config fields:

```json
"exposure_compensation": 0.0,
"awb_mode": "auto",
"colour_gains_red": 0.0,
"colour_gains_blue": 0.0,
"awb_settle_seconds": 0.5
```

Manual `ColourGains` are only sent when both red and blue gains are above zero. Setting manual gains disables auto white balance.

If `auto_white_balance` is false but manual gains are not given, the service lets AWB settle briefly before disabling AWB, so it can lock the current AWB result rather than locking immediately at startup.

### Status reporting

Camera status now includes extra diagnostic fields:

- `last_capture_source`
- `last_array_color_order`
- `last_metadata`
- `libcamera_controls_available`

### Error codes

Added:

- `PISD-CAM-008` - camera colour control / AWB mode / array colour-order handling warning or failure
- `PISD-TEST-005` - camera colour diagnostic script did not save all expected frames

## New test commands

Main hardware camera test with preferred request path:

```bash
python scripts/test_camera_service.py --hardware --capture-source request
```

Colour diagnostic batch:

```bash
python scripts/diagnose_camera_color.py --hardware
```

This writes files to:

```text
PiSD/test_outputs/camera_color/
```

Important outputs:

- `01_request_awb_auto.jpg` - preferred default preview baseline
- `02_request_awb_off_lock.jpg` - AWB settles, then gets locked
- `03_array_auto.jpg` - array path with automatic colour interpretation
- `04_array_rgb_interpretation.jpg` - array path forced as RGB
- `05_array_bgr_interpretation.jpg` - array path forced as BGR

Optional:

```bash
python scripts/diagnose_camera_color.py --hardware --include-rgb-format
```

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile` on updated service, core, and scripts.
- `python3 PiSD.py --status-only` in simulation mode.
- `python3 scripts/check_error_reporting.py`.
- `python3 scripts/check_service_imports.py`.
- `python3 scripts/test_camera_service.py` in simulation mode.
- `python3 scripts/diagnose_camera_color.py` in simulation mode.
- `python3 scripts/test_motor_service.py` in simulation mode.
- Confirmed final zip contains only the `PiSD/` folder.
- Confirmed only `requirements.txt` exists; no `requirement.txt` was restored.

## Not verified here

- Real Raspberry Pi camera colour output, because the packaging environment has no Raspberry Pi camera attached.
- Real GPIO motor output.
- Browser visual inspection of the saved hardware colour frames.

## Next steps on the Pi

Run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/diagnose_camera_color.py --hardware
```

Then compare:

```text
test_outputs/camera_color/01_request_awb_auto.jpg
test_outputs/camera_color/02_request_awb_off_lock.jpg
test_outputs/camera_color/03_array_auto.jpg
test_outputs/camera_color/04_array_rgb_interpretation.jpg
test_outputs/camera_color/05_array_bgr_interpretation.jpg
```

If `01_request_awb_auto.jpg` is correct, keep `capture_source: request` for preview.

If request images are still wrong, test manual colour gains or camera tuning next.
