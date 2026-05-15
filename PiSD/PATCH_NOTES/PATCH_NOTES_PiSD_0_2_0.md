# PiSD 0.2.0 Stable Baseline Notes

## Request summary

The user asked to pack the current PiSD state into version 2 before starting the GUI update.

This is a full stable package, not a patch-only zip.

## Baseline promoted

Promoted to:

```text
PiSD_0_2_0
```

## Source packages applied

This full package was built by applying the accepted patch-only updates onto the previous stable package:

1. `PiSD_0_1_0.zip` full stable package
2. `PiSD_0_1_1_patch.zip` motor channel calibration patch
3. `PiSD_0_1_2_patch.zip` standard validation patch

## Files changed for this stable promotion

```text
PiSD/pisd/__init__.py
PiSD/README.md
PiSD/docs/STABLE_BASELINE.md
PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_0.md
```

## Included accepted behavior

This stable baseline includes:

- Picamera2 camera service with OV5647 hardware support
- request/PIL visual capture path
- `array_color_order: rgb` as the confirmed raw array/CV path
- camera setting controls/tests for size, FPS, exposure, gain, AWB, colour gains, quality, buffer count, flips, and image controls
- RPi.GPIO motor service with simulation fallback
- one-by-one motor channel testing for different car wiring
- local API endpoint for motor channel testing
- shared `PISD-*` error code and reporting system
- standard OK/FAIL validation script
- single dependency file: `PiSD/requirements.txt`

## User hardware evidence incorporated

The user-provided Raspberry Pi logs showed:

- `PiSD.py --status-only` returned `PISD-OK-000`
- error reporting test returned `PISD-OK-000`
- Picamera2, OpenCV, PIL, Flask, requests, numpy, and RPi.GPIO were available
- hardware camera capture started with Picamera2 on OV5647
- `01_request_awb_auto` was accepted as the correct visual colour reference
- `91_array_rgb_confirmed_correct` was accepted as the correct array/CV colour reference
- motor simulation and real GPIO adapter paths returned clean status
- live API status, camera start, camera frame, motor config, invalid input handling, and stop endpoints worked

## Verification performed during packaging

Performed locally in the packaging environment:

- extracted `PiSD_0_1_0.zip`
- overlaid `PiSD_0_1_1_patch.zip`
- overlaid `PiSD_0_1_2_patch.zip`
- updated package version to `0.2.0`
- updated stable baseline documentation
- ran Python compile checks across PiSD files
- ran `python3 PiSD.py --status-only`
- ran `python3 scripts/check_error_reporting.py`
- ran `python3 scripts/run_standard_validation.py --skip-api`
- checked zip has one top-level `PiSD/` folder
- checked there is no duplicate `requirement.txt`
- checked Python cache folders were excluded

## Known limits

- Real hardware was not retested in this packaging environment. Hardware evidence comes from the user-provided Raspberry Pi logs.
- GUI work has not started yet.
- Final motor direction should remain configurable in the future GUI settings page because car wiring differs.

## Next recommended patch

`PiSD_0_2_1_patch`: first web GUI/server page patch, built on top of this stable baseline.
