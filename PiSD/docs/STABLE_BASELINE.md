# PiSD Stable Baseline

## Stable version

`PiSD_0_5_0`

This is the fifth stable PiSD baseline package. It is built from the full `PiSD_0_4_0` package plus the accepted `0_4_1` through `0_4_10` patches.

## Baseline purpose

PiSD is the clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

This stable baseline should be used as the rollback point for future PiSD manual-drive, GUI, recording, preview, overlay, and runtime-service development unless the user promotes a newer version.

## Included accepted work

`PiSD_0_5_0` includes the tested hardware-service foundation from earlier baselines, the v4 GUI/runtime work, and the accepted v4 patch-line improvements:

- Picamera2 camera service with request/PIL visual preview and confirmed RGB array/CV reference.
- RPi.GPIO-style motor service with safe simulation fallback.
- Shared `PISD-*` error-code reporting and standard OK/FAIL validation script.
- One-by-one motor channel calibration and `POST /api/motor/test-channel`.
- Front page mode selector, settings page, dashboard, testing pages, and panel/presentation tooling.
- Responsive layout system loaded consistently across GUI pages.
- Manual Drive page with compact status, camera preview, drag-pad drive control, emergency stop, capture, recording, and recording-library management.
- Manual Drive overlay toggle on the Manual Drive page.
- Sampled predicted-arc overlay based on throttle and steering, including forward/reverse/stopped visual states.
- Overlay calibration controls for path length, curve strength, opacity, and path width.
- Overlay/source debug display for steering, throttle, left/right motor output, and source state.
- Clear Start camera / Live stream / Stop camera only / STOP motors / Refresh status behavior.
- Status-only refresh that does not start the camera and does not send motor commands.
- Page-leave motor fail-safe stop using browser keepalive/sendBeacon where available.
- Manual Drive preview idle start, FPS estimate, frame age, stale-frame warning, and guarded preview metrics loop.
- Recording service with per-session recording folders, daily single-capture folders, traceable frame IDs, and `records.jsonl` metadata.
- Recording/snapshot library APIs to list, zip-download, and delete selected folders.
- Recording/snapshot selected-folder UI details and safer download/delete button states.
- Hardened backend folder-id validation so unsafe root-level ids such as `.` are rejected.
- Manual drive speed and steering controls able to reach `1.0`.

## Confirmed service status from user Pi hardware logs

Earlier PiSD hardware tests on the Raspberry Pi confirmed:

- `PiSD.py --status-only` returned `PISD-OK-000`.
- error reporting schema test returned `PISD-OK-000` and generated a structured synthetic error.
- Picamera2, OpenCV, PIL, Flask, requests, numpy, and RPi.GPIO were detected.
- hardware camera capture started with Picamera2.
- visual camera frame capture returned a JPEG frame through the live API.
- `03_request_awb_off_lock` is the trusted default visual colour reference.
- `91_array_rgb_confirmed_correct` is the confirmed raw array/CV colour reference.
- motor simulation produced expected numeric mixing results.
- real GPIO motor adapter reported `hardware_enabled: true` and `adapter: rpigpio`.
- live API status, camera start, camera frame, motor config, invalid-input error handling, and stop endpoints worked.

## Remaining physical checks

Final wheel direction is car-specific and should be adjusted through GUI settings. Before floor-driving, use lifted-wheel tests to confirm each car's wiring and safe speed limits.

For this stable GUI baseline, test on the Pi browser after applying the package:

- front page loads compactly;
- settings save and apply across pages;
- Manual Drive status/preview/control layout is usable on PC/iPad/phone;
- drag pad sends movement only after safety lock is armed;
- STOP motors remains available and works;
- overlay toggle is visible on the Manual Drive page;
- predicted arc follows throttle/steering and returns to stopped state after STOP;
- Start camera, Live stream, Stop camera only, Refresh status, and STOP motors keep separate meanings;
- preview FPS/frame-age/stale indicators update while live preview is active;
- capture saves to the daily single-captures folder;
- recording creates its own session folder with frames and `records.jsonl`;
- recording/snapshot folders can be listed, zip-downloaded, and deleted only from safe selected folders.

## Future patch rule

Future PiSD patches after this baseline should use `0_5_x` naming, such as `PiSD_0_5_1_patch.zip`, unless the user promotes a newer stable line.

Patch-only zips should contain only:

- changed files;
- new files;
- required patch notes.

Full packages should only be created when the user asks for a stable/full package.
