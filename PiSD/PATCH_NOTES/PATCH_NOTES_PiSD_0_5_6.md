# PiSD 0.5.6 Patch Notes — OV5647 default camera colour profile

## Request summary

Set the correct tested OV5647 camera colour profile as the default PiSD camera setting, while preserving the accepted PiSD 0.5.x AI Mode, Manual Drive, overlay, and reverse-steering behaviour.

## Cause / root cause

The earlier default camera profile still used AWB-auto (`01_request_awb_auto`). Hardware comparison showed:

- `01` was too red / partly blue.
- `02` was too yellow.
- `03` was better than `01`.
- `06` was too blue.
- `90` and `92` were wrong colour-order diagnostics.
- `91` looked like `03`, confirming RGB handling was correct.

Therefore PiSD should default to the `03_request_awb_off_lock` style visual profile and keep the request/PIL RGB preview path for training capture.

## Files changed

- `PiSD/config/defaults.json`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/app.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/scripts/diagnose_camera_color.py`
- `PiSD/scripts/test_camera_settings_matrix.py`
- `PiSD/docs/CAMERA_SETTINGS.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/FUTURE_CODE_RULES.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/README.md`

## Behaviour changed

### Default camera profile

The default camera profile is now:

```json
{
  "capture_source": "request",
  "array_color_order": "rgb",
  "format": "BGR888",
  "auto_white_balance": false,
  "awb_mode": "auto",
  "colour_gains_red": 0.0,
  "colour_gains_blue": 0.0,
  "awb_settle_seconds": 1.0,
  "brightness": 0.0,
  "contrast": 1.0,
  "saturation": 1.0
}
```

### AWB settle then lock

`CameraService` now supports the intended lock behaviour for this profile:

1. start camera with AWB temporarily enabled,
2. wait for `awb_settle_seconds`,
3. apply the normal locked profile with `AwbEnable = false`.

This keeps the default closer to the tested `03_request_awb_off_lock` diagnostic instead of disabling AWB before it can settle.

### Runtime settings migration

Existing `config/runtime_settings.json` files are migrated only when their camera settings still match the old uncustomised AWB-auto default. User-customised camera settings such as daylight/tungsten/manual gain profiles are preserved.

### Manifest/docs

The testing manifest and docs now identify:

- visual default/reference: `03_request_awb_off_lock`
- raw array/CV reference: `91_array_rgb_confirmed_correct`

## Verification actually performed

- `python3 -m compileall PiSD/pisd PiSD/scripts`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_ai_drive_service.py`
- `python3 scripts/test_camera_service.py --seconds 0.6 --min-frames 1 --output test_outputs/camera_service_default_profile.jpg`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Known limits / next steps

- Real Pi camera colour was not re-captured in this container; the default is based on the user-provided hardware comparison results.
- If the Pi already has a deliberately customised runtime camera profile, it will be preserved. Use Settings reset or `/api/camera/apply` if you want to force the new profile manually.
