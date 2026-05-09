# PiSD 0.0.6 Patch Notes — lock confirmed colour references

## Request summary

User reported that colour diagnostic outputs `01` and `91` are correct. User also requested future delivery as patch-only changed files.

## Cause / context

PiSD 0.0.5 exposed both the request/PIL visual path and optional raw array diagnostics. Hardware testing on the OV5647 camera showed:

- `01_request_awb_auto` is the correct visual preview baseline.
- `91_array_rgb` is the correct raw array/CV colour interpretation.
- Earlier auto/BGR array interpretations should not be used as defaults.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/config/defaults.json`
- `PiSD/scripts/diagnose_camera_color.py`
- `PiSD/scripts/test_camera_settings_matrix.py`
- `PiSD/docs/CAMERA_SETTINGS.md`
- `PiSD/docs/HARDWARE_SERVICES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/FUTURE_CODE_RULES.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_6.md`

## Behaviour changed

- PiSD version updated to `0.0.6`.
- Default visual capture remains `capture_source: "request"`.
- Default raw array interpretation changed from `array_color_order: "auto"` to `array_color_order: "rgb"`.
- Camera capability output now reports:
  - `recommended_visual_capture_source: "request"`
  - `recommended_array_color_order: "rgb"`
  - `verified_colour_reference: "01_request_awb_auto"`
  - `verified_array_reference: "91_array_rgb"`
- Colour diagnostic notes now identify `01_request_awb_auto` and `91_array_rgb` as the known-good references.
- Settings matrix notes now recommend RGB for future raw array/CV testing.

## Error handling / reporting

No new error codes were required. Existing camera setting validation and diagnostics remain in place:

- `PISD-CAM-008` for colour-control failures
- `PISD-CAM-009` for invalid/ignored camera settings
- `PISD-TEST-005` for colour diagnostic failures
- `PISD-TEST-006` for settings matrix failures

## Verification actually performed

Performed locally in the packaging environment:

- Python compile check on changed modules and scripts.
- `python3 PiSD.py --status-only` in simulation mode.
- `python3 scripts/test_camera_service.py --capture-source request` in simulation mode.
- `python3 scripts/test_camera_service.py --capture-source array --array-color-order rgb` in simulation mode.
- `python3 scripts/diagnose_camera_color.py --include-array-diagnostics` in simulation mode.
- `python3 scripts/test_camera_settings_matrix.py --include-array-diagnostics` in simulation mode.
- Confirmed the patch zip contains only changed/new files and patch notes.

## Not verified here

- Real OV5647 camera output after this default change. The user-provided hardware result is the source for choosing `01` and `91` as the known-good references.
- Real motor hardware, because this patch only changes camera colour defaults/docs.

## Next steps on the Pi

After applying this patch, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_camera_service.py --hardware --capture-source request
python3 scripts/test_camera_service.py --hardware --capture-source array --array-color-order rgb --output test_outputs/array_rgb.jpg
python3 scripts/diagnose_camera_color.py --hardware --include-array-diagnostics
```

Expected references:

- visual preview: `01_request_awb_auto`
- raw array/CV: `91_array_rgb_confirmed_correct`
