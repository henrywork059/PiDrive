# PiSD 0.1.0 Stable Baseline Notes

## Request summary

Package the accepted PiSD work as a stable full-version baseline after the camera, motor, error-reporting, and live API tests passed on the user's Raspberry Pi.

## Baseline source

This full package is built from:

1. `PiSD_0_0_5.zip` full package
2. `PiSD_0_0_6_patch.zip` accepted patch-only update
3. stable baseline metadata added in this package

## Files changed for stable promotion

- `PiSD/pisd/__init__.py`
  - promoted package version from `0.0.6` to `0.1.0`
- `PiSD/README.md`
  - updated current version to `PiSD_0_1_0`
  - added stable baseline notes based on user hardware logs
  - added `docs/STABLE_BASELINE.md` and this patch note to the folder map
- `PiSD/docs/STABLE_BASELINE.md`
  - added stable baseline status, confirmed tests, and future patch rules
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_1_0.md`
  - this stable baseline note

## Behaviour promoted into stable baseline

The stable baseline keeps the accepted PiSD 0.0.6 behaviour:

- one dependency file only: `PiSD/requirements.txt`
- `PiSD.py` main launcher
- safe simulation mode by default
- real hardware only when `--hardware` is used
- structured error codes and error reports
- Picamera2 camera service
- RPi.GPIO-style motor service with simulation fallback
- full camera settings coverage for size, FPS, exposure, AWB, colour gains, quality, buffer count, queue, image controls, flip, noise reduction, and scaler crop
- visual capture default: `capture_source=request`
- raw array/CV default: `array_color_order=rgb`
- colour references:
  - `01_request_awb_auto` for visual preview/capture
  - `91_array_rgb_confirmed_correct` for raw array/CV path

## Verification actually performed locally while packaging

- extracted `PiSD_0_0_5.zip`
- overlaid `PiSD_0_0_6_patch.zip`
- updated stable version metadata
- ran Python compile check on launcher, services, app, core modules, and scripts
- ran `python3 PiSD.py --status-only` in local simulation mode
- checked that no duplicate `requirement.txt` exists
- checked that the final zip contains a single top-level `PiSD/` folder

## Hardware verification source

Real hardware verification was performed by the user on the Raspberry Pi, not inside this packaging environment.

The user-provided logs showed:

- `PISD-OK-000` status and error reporting checks
- real Picamera2 OV5647 camera startup and JPEG frame capture
- camera colour confirmation for `01_request_awb_auto` and `91_array_rgb_confirmed_correct`
- motor simulation and real GPIO motor adapter success
- live API status, camera start, frame, motor config, stop, and structured invalid JSON error handling

## Known limits / next steps

- The logs confirm GPIO commands were accepted, but physical wheel direction must still be confirmed by observation with the wheels lifted.
- The current Flask server is still a development server. A production WSGI server can be added later if PiSD becomes the main runtime.
- The next major stage is building the real PiSD GUI/web control page on top of the now-tested camera and motor APIs.
