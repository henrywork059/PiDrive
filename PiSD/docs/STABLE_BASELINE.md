# PiSD Stable Baseline

## Stable version

`PiSD_0_9_0`

This is the ninth stable PiSD baseline package. It is built from the full `PiSD_0_8_0` package plus the accepted `0_8_1` through `0_8_11` patch line and the Manual Drive keyboard-control update.

## Baseline purpose

PiSD is the clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

This stable baseline should be used as the rollback point for future PiSD manual-drive, GUI, recording, preview, overlay, AI Mode, steering-algorithm, motor-tuning, safety-policy, and runtime-service development unless the user promotes a newer version.

## Included accepted work

`PiSD_0_9_0` includes the tested hardware-service foundation from earlier baselines, the accepted v6 AI/manual-drive/runtime work, the accepted v7 overlay/recording metadata patch line, and the accepted 0_8_x steering, overlay, recording, motor-tuning, and keyboard-control patch line:

- Picamera2 camera service with request/PIL visual preview path and simulation fallback.
- RPi.GPIO-style motor service with safe simulation fallback.
- Shared `PISD-*` error-code reporting and standard OK/FAIL validation script.
- One-by-one motor channel calibration and `POST /api/motor/test-channel`.
- Front page mode selector, settings page, dashboard, testing pages, and panel/presentation tooling.
- Manual Drive page with compact status, camera preview, drag-pad and keyboard drive control, emergency stop, capture, recording, and recording-library management.
- Manual Drive recording sessions write trainer-friendly `labels.jsonl` beside full `records.jsonl` metadata.
- Recording/snapshot APIs list, zip-download, and delete selected safe folders.
- Manual Drive and AI Mode road-guide overlay now use a shared filled path-corridor renderer.
- Turning overlay uses sampled kinematic-style geometry with tangent-normal road-edge offsets.
- Overlay left/right steering direction is corrected in the shared helper.
- Reverse-motion overlay drawing remains hidden.
- Manual Drive overlay settings now use number inputs in a larger popup instead of sliders/drop-down controls.
- Overlay values are no longer clamped back to the old slider ranges when typed or saved.
- Manual Drive overlay tuning is reduced to seven visual-only controls, and `overlay_settings.json` sidecars are saved for recordings and snapshots.
- Screenshots and continuous recordings save overlay metadata in `manifest.json`, `records.jsonl`, `labels.jsonl`, `overlay_settings.json`, and `overlay_settings_history.jsonl` so piTrainer can redraw the path later.
- AI Mode page at `/ai-mode`, model discovery/loading from `PiSD/models/`, and guarded safety limiter before motor output.
- Retired Autopilot compatibility path points users to AI Mode instead of scripted movement.
- Page-leave motor fail-safe stop.
- Manual Drive supports keyboard control: ↑/↓ adjust live throttle by `0.05` per press, holding ←/→ ramps steering by full scale in `0.8 s`, and Space stops.
- Manual Drive no longer overrides saved motor `steer_mix` with a per-command `1.0` value.
- AI steering-only mode keeps fixed throttle while driving straight.
- AI motor-output enable is live/session-only and no longer persisted in `runtime_settings.json`.
- Dashboard is labelled as a legacy/development comparison shell.
- Default motor steering mode is now `turn_rate`, where left/right input controls curve tightness and up/down controls travel speed along that curve. The older `arcade_mix` mixer remains selectable as a fallback.
- Manual Drive and AI Mode overlays are visual-only calibration layers. In patches after this stable baseline, overlay matching is tuned manually against real camera frames and real motion instead of following motor Turn Gain.
- `/motor-tuning` is intentionally reset to a clean placeholder after `0_8_7`; backend timed test and start-dead-zone logic remain available for the next rebuild.

## Confirmed service status from earlier user Pi hardware logs

Earlier PiSD hardware tests on the Raspberry Pi confirmed:

- `PiSD.py --status-only` returned `PISD-OK-000`.
- error reporting schema test returned `PISD-OK-000` and generated a structured synthetic error.
- Picamera2, OpenCV, PIL, Flask, requests, numpy, and RPi.GPIO were detected.
- hardware camera capture started with Picamera2.
- visual camera frame capture returned a JPEG frame through the live API.
- motor simulation produced expected numeric mixing results.
- real GPIO motor adapter reported `hardware_enabled: true` and `adapter: rpigpio`.
- live API status, camera start, camera frame, motor config, invalid-input error handling, and stop endpoints worked.

## Camera colour note

The package includes the attempted `03_request_awb_off_lock` default visual profile and the `91_array_rgb_confirmed_correct` diagnostic reference from earlier hardware testing. Because this packaging container cannot verify OV5647 colour output, treat camera colour as a known hardware-verification item for a future `0_9_x` patch if the Pi still shows the old colour behaviour.

## Remaining physical checks

Final wheel direction is car-specific and should be adjusted through GUI settings. Before floor-driving, use lifted-wheel tests to confirm each car's wiring and safe speed limits.

For this stable GUI baseline, test on the Pi browser after applying the package:

- front page loads compactly;
- settings save and apply across pages;
- Manual Drive status/preview/control layout is usable on PC/iPad/phone;
- drag pad and keyboard control send movement only after safety lock is armed;
- keyboard test: enable motor output with wheels lifted, press ↑/↓ for ±0.05 throttle steps, hold ←/→ to ramp steering, then press Space to stop;
- `/api/control/manual` refuses non-zero hardware commands without live safety/motor-output acknowledgement;
- STOP motors remains available and works;
- overlay toggle is visible on Manual Drive and AI Mode pages;
- overlay settings popup opens and number inputs save the values typed by the user;
- road-guide overlay bends in the intended screen direction for left/right steering;
- Start camera, Live stream, Stop camera only, Refresh status, and STOP motors keep separate meanings;
- preview FPS/frame-age/stale indicators update while live preview is active;
- capture saves to the daily single-captures folder and includes overlay metadata;
- recording creates its own session folder with frames, `manifest.json`, `records.jsonl`, and `labels.jsonl`, including overlay metadata;
- recording/snapshot folders can be listed, zip-downloaded, and deleted only from safe selected folders;
- AI Mode can load a runnable model from `PiSD/models/` and keeps motor-output enable session-only.

## Future patch rule

Future PiSD patches after this baseline should use `0_9_x` naming, such as `PiSD_0_9_1_patch.zip`, unless the user promotes a newer stable line.

Patch-only zips should contain only:

- changed files;
- new files;
- required patch notes.

Full packages should only be created when the user asks for a stable/full package.
