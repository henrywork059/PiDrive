# PiSD Camera Settings Reference

PiSD camera code must keep all camera changes observable and testable. Every camera setting should be visible through:

- `config/defaults.json`
- `CameraService.status()`
- `GET /api/camera/config`
- `GET /api/camera/capabilities`
- one or more scripts in `scripts/`
- a PiSD error code when a setting is rejected, clamped, ignored, or fails on hardware

## Visual preview path

Use this for GUI preview, saved test frames, and colour checking:

```json
"capture_source": "request"
```

This uses Picamera2 request images and Pillow JPEG encoding. It is the trusted visual path because raw array/OpenCV paths can have RGB/BGR interpretation issues.

## Raw array path

Use this only for diagnostics or future computer vision pipelines:

```json
"capture_source": "array"
```

Known note from hardware testing: `01_request_awb_auto` was confirmed correct for visual preview, and `91_array_rgb` was confirmed correct for the raw array/CV path. Earlier auto/BGR array outputs were wrong, so array modes remain optional diagnostics and default to RGB.

## Main configuration settings

| Setting | Purpose | Restart needed |
|---|---|---|
| `width` | main stream width | yes |
| `height` | main stream height | yes |
| `fps` | target frame rate; maps to `FrameDurationLimits` | yes |
| `format` | Picamera2 stream format such as `BGR888` or `RGB888` | yes |
| `preview_quality` | JPEG output quality, 20-95 | no |
| `buffer_count` | Picamera2 buffer count | yes |
| `queue` | Picamera2 queue mode | yes |
| `hflip` | horizontal camera transform | yes |
| `vflip` | vertical camera transform | yes |

## Exposure settings

| Setting | Purpose |
|---|---|
| `auto_exposure` | true = let AE run; false = use manual exposure/gain |
| `exposure_us` | manual exposure time in microseconds |
| `analogue_gain` | manual sensor gain |
| `exposure_compensation` | AE exposure value compensation |
| `ae_metering_mode` | `centre-weighted`, `spot`, `matrix`, or `custom` |
| `ae_exposure_mode` | `normal`, `short`, `long`, or `custom` |
| `ae_constraint_mode` | `normal`, `highlight`, `shadows`, or `custom` |

## White balance and colour settings

| Setting | Purpose |
|---|---|
| `auto_white_balance` | true = AWB enabled; false = manual colour gains |
| `awb_mode` | `auto`, `daylight`, `cloudy`, `indoor`, `fluorescent`, `tungsten`, `incandescent`, `custom` |
| `colour_gains_red` | manual red gain; applies only when AWB is off |
| `colour_gains_blue` | manual blue gain; applies only when AWB is off |
| `awb_settle_seconds` | delay after start before first checks/captures |
| `brightness` | image brightness control |
| `contrast` | image contrast control |
| `saturation` | image saturation control |
| `sharpness` | image sharpness control |

## Other controls

| Setting | Purpose |
|---|---|
| `noise_reduction_mode` | `off`, `fast`, `high-quality`, `minimal`, or `zsl` when supported |
| `scaler_crop` | optional crop as `[x, y, width, height]` or `x,y,width,height` |
| `array_color_order` | array path interpretation: `auto`, `bgr`, `rgb`, `bgra`, `rgba`, `swap_rb`, `none`; default/recommended = `rgb` |

## Main test commands

Dump hardware capabilities:

```bash
python3 scripts/dump_camera_capabilities.py --hardware
```

Basic camera test with request/PIL visual path:

```bash
python3 scripts/test_camera_service.py --hardware --capture-source request
```

Test size, buffer, queue, and JPEG quality:

```bash
python3 scripts/test_camera_service.py --hardware --width 640 --height 360 --fps 15 --preview-quality 80 --buffer-count 4 --no-queue
```

Test manual exposure:

```bash
python3 scripts/test_camera_service.py --hardware --manual-exposure --exposure-us 8000 --analogue-gain 1.5
```

Test AWB mode:

```bash
python3 scripts/test_camera_service.py --hardware --awb-mode daylight
```

Test manual white balance gains:

```bash
python3 scripts/test_camera_service.py --hardware --awb-off --colour-gains 1.8,1.2
```

Run the settings matrix:

```bash
python3 scripts/test_camera_settings_matrix.py --hardware
```

Run optional array diagnostics only when needed:

```bash
python3 scripts/test_camera_settings_matrix.py --hardware --include-array-diagnostics
python3 scripts/diagnose_camera_color.py --hardware --include-array-diagnostics
python3 scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb
```

## Error-code expectation

Camera setting problems must be reported with camera or test error codes. Current relevant codes:

- `PISD-CAM-003` control apply failed
- `PISD-CAM-008` colour control failed
- `PISD-CAM-009` invalid/ignored setting
- `PISD-CAM-010` capability query failed
- `PISD-TEST-005` colour diagnostic failed
- `PISD-TEST-006` camera settings matrix failed
