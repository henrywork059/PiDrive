# PiSD Stable Baseline

## Stable version

`PiSD_0_2_0`

This is the second stable PiSD baseline package. It is built from the full `PiSD_0_1_0` package plus the accepted patch-only updates `PiSD_0_1_1` and `PiSD_0_1_2`.

## Baseline purpose

PiSD is the clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

This stable baseline should be used as the rollback point for future PiSD GUI/server development unless the user promotes a newer version.

## Included accepted work

`PiSD_0_2_0` includes:

- the tested camera service foundation from `PiSD_0_1_0`
- the tested motor service foundation from `PiSD_0_1_0`
- shared `PISD-*` error-code reporting
- trusted OV5647 visual reference: `01_request_awb_auto`
- trusted raw array/CV reference: `91_array_rgb_confirmed_correct`
- one-by-one motor channel calibration from `PiSD_0_1_1`
- `POST /api/motor/test-channel` for local API-to-hardware motor channel testing
- standard OK/FAIL validation script from `PiSD_0_1_2`

## Confirmed service status from user Pi hardware logs

The user ran PiSD on a Raspberry Pi with an OV5647 camera and GPIO motor wiring. The logs confirmed:

- `PiSD.py --status-only` returned `PISD-OK-000`.
- error reporting schema test returned `PISD-OK-000` and generated a structured synthetic error.
- Picamera2, OpenCV, PIL, Flask, requests, numpy, and RPi.GPIO were detected.
- hardware camera capture started with Picamera2.
- visual camera frame capture returned a JPEG frame through the live API.
- `01_request_awb_auto` is the trusted visual colour reference.
- `91_array_rgb_confirmed_correct` is the confirmed raw array/CV colour reference.
- motor simulation produced expected numeric mixing results.
- real GPIO motor adapter reported `hardware_enabled: true` and `adapter: rpigpio`.
- live API status, camera start, camera frame, motor config, invalid-input error handling, and stop endpoints worked.

## Remaining physical check

Final wheel direction is car-specific and should be adjusted later in the GUI settings page. Before floor-driving, use the lifted-wheel motor channel test to confirm each car's wiring:

- left motor direction 1 / direction 2
- right motor direction 1 / direction 2
- low-speed startup threshold
- stable test speed
- stop after every test step

## Future patch rule

Future PiSD patches should be patch-only unless a full stable package is explicitly requested.

Patch-only zips should contain only:

- changed files
- new files
- required patch notes

Full packages should only be created when the user asks for a stable/full package.

The next expected patch after this baseline is the first GUI/server page patch.
