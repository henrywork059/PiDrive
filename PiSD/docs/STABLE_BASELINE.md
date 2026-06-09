# PiSD Stable Baseline

## Stable version

`PiSD_0_10_0`

This is the tenth stable PiSD baseline package. It is built from the accepted `PiSD_0_9_0` stable package plus the accepted `0_9_1` through `0_9_10` patch line.

## Baseline purpose

PiSD is the clean sandbox under `PiDrive/PiSD` for rebuilding and testing PiServer GUI and runtime functions from square one.

This stable baseline should be used as the rollback point for future PiSD manual-drive, GUI, recording, preview, overlay, AI Mode, steering-algorithm, motor-tuning, safety-policy, and runtime-service development unless the user promotes a newer version.

## Included accepted work

`PiSD_0_10_0` includes the tested hardware-service foundation from earlier baselines, the accepted v6 AI/manual-drive/runtime work, the accepted v7 overlay/recording metadata patch line, the accepted 0_8_x steering/overlay/recording/motor-tuning reset work, and the accepted 0_9_x keyboard, AI runtime, model loading, recording, and control-loop patch line:

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
- `/motor-tuning` is intentionally reset to a clean placeholder after `0_8_7`; backend timed test logic remains available for the next rebuild.

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

The package includes the attempted `03_request_awb_off_lock` default visual profile and the `91_array_rgb_confirmed_correct` diagnostic reference from earlier hardware testing. Because this packaging container cannot verify OV5647 colour output, treat camera colour as a known hardware-verification item for a future `0_10_x` patch if the Pi still shows the old colour behaviour.

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
- Start live is the short user-facing live-preview action in Manual Drive and AI Mode; Stop camera only, Refresh status, and STOP motors keep separate meanings;
- preview FPS/frame-age/stale indicators update while live preview is active;
- capture saves to the daily single-captures folder and includes overlay metadata;
- recording creates its own session folder with frames, `manifest.json`, `records.jsonl`, and `labels.jsonl`, including overlay metadata;
- recording/snapshot folders can be listed, zip-downloaded, and deleted only from safe selected folders;
- AI Mode can load a runnable model from `PiSD/models/` and keeps motor-output enable session-only.
- AI Mode can upload/delete model files safely inside `PiSD/models/` and reports clearer load/runtime diagnostics.
- TFLite model loading supports piTrainer exports more reliably, including single-output `[steering, throttle]`, multi-output fallback handling, quantized input/output handling, and NumPy tensor shape handling.
- AI runtime setup guidance and helper scripts are included for Pis missing `tflite_runtime`, `ai_edge_litert`, or TensorFlow Lite.
- AI control loop uses cached camera frames to better follow the configured Update Hz; the allowed AI update-rate maximum is now `60`.
- Manual Drive and AI Mode expose one short Start live action; Dashboard and Testing Server keep one technical camera/live diagnostic action; camera/live/record/run controls stay above the preview image so they remain visible before the user looks at the frame.
- AI Mode recording and snapshot buttons use the shared recording service and include overlay sidecar metadata.
- AI Mode `Limiter / correction` adds a correction pane with Manual Drive-style drag-pad/arrow-key additive AI correction, user-settable correction percentage, `r` recording shortcut, and `s` snapshot shortcut; fixed-throttle mode still enforces fixed throttle after correction.
- Motor dead-zone/start-kick code added during the v9 patch line was later removed; this baseline does not include that feature.

## Future patch rule

Future PiSD patches after this baseline should use `0_10_x` naming, such as `PiSD_0_10_11_patch.zip`, unless the user promotes a newer stable line.

Patch-only zips should contain only:

- changed files;
- new files;
- required patch notes.

Full packages should only be created when the user asks for a stable/full package.


## PiSD 0.10.5 maintainability patch

`PiSD_0_10_5_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_4`. It does not promote a new stable rollback baseline.

Main structural update:

- AI correction equation helpers moved into `pisd/services/ai_correction.py`.
- AI safety limiter helpers moved into `pisd/services/ai_safety.py`.
- `AIDriveService` remains the live runtime coordinator for model loading, camera frames, prediction loop, and motor calls.
- The additive correction equation remains `corrected = AI + manual * Correction %`.
- Fixed-throttle mode still applies after correction through the same safety path.

This makes the newest AI correction work easier to test without real camera, model, Flask, or motor dependencies while preserving the accepted v10 behaviour.


## PiSD 0.10.6 AI Mode manual-pad patch

`PiSD_0_10_6_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_5`. It does not promote a new stable rollback baseline.

Main UI/runtime update:

- AI Mode `Limiter / correction` is now `Limiter / correction / manual`.
- The tab strip has three panes: Limiter, Correction, and Manual pad.
- The Manual pad is a direct takeover pad that sends guarded `/api/control/manual` commands using drag input and arrow-key driving.
- Shared safety acknowledgement and motor-output enable controls are outside the toggled pane content, so they remain visible from all three modes.
- There is still only one `Save AI settings` configuration button, kept in the panel header outside the toggled content.

Rollback safety: this patch preserves the accepted one-button `Start live` workflow, AI snapshot/record buttons and shortcuts, additive correction equation, fixed-throttle-after-correction behaviour, and the `0_10_5` helper-module split.



## PiSD 0.10.11 AI text and one-confirmation patch

`PiSD_0_10_11_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_10`. It does not promote a new stable rollback baseline.

Scope:
- Shortens AI Mode descriptive text.
- Replaces the separate AI safety acknowledgement and motor-output checkboxes with one visible confirmation checkbox.
- Keeps backend guard semantics unchanged by sending both `safety_ack` and `enable_motor_output` when the single confirmation is checked.

Rollback safety: preserves the accepted one-button live workflow, AI correction/manual-pad behaviour, global Space STOP, shared recording download panel, max-throttle persistence, top-of-preview button placement, and original frame-id restore.

## PiSD 0.10.10 original frame-id restore patch

`PiSD_0_10_10_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_9`. It does not promote a new stable rollback baseline.

- Restores the original PiSD recording filename format: `frame_000001_<utc-stamp>_<uuid>.jpg`.
- Restores the original `records.jsonl` frame-id format: `<session_id>_000001_<utc-stamp>_<uuid>`.
- Removes the experimental `frame_id_scheme` / `frame_id_unique_scope` fields added in `0_10_9` from new recording metadata.
- Restores the original compact `labels.jsonl` schema without extra global-id fields.
- Preserves the `0_10_9` top-of-preview button placement changes.

Rollback safety: this patch preserves the accepted one-button live workflow, AI correction/manual-pad behaviour, global Space STOP, shared recording download panel, max-throttle persistence, and preview button placement.

## PiSD 0.10.9 preview buttons and frame-id patch

`PiSD_0_10_9_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_8`. It does not promote a new stable rollback baseline.

- Preview action buttons now stay above the preview image on Manual Drive, AI Mode, Dashboard, and Testing Server.
- Recording frame IDs use a globally unique session/date/UUID-based format and are written into both `records.jsonl` and `labels.jsonl`.

Rollback safety: this patch preserves the accepted one-button live workflow, AI correction/manual-pad behaviour, global Space STOP, shared recording download panel, and max-throttle persistence.

## PiSD 0.10.8 AI max-throttle persistence patch

`PiSD_0_10_8_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_7`. It does not promote a new stable rollback baseline.

This patch fixes AI Mode limiter settings being repainted from old/default status values while the user is editing. `Max throttle` now gets a dirty-field guard and auto-save path so it persists through status refresh, page reload, and restart once saved to `config/runtime_settings.json`.

Rollback safety: the patch does not change AI runtime math, model loading, recording folders, camera startup, motor mapping, Space STOP, or Manual pad behaviour.


## PiSD 0.10.7 AI recording panel and global Space STOP patch

`PiSD_0_10_7_patch.zip` builds forward from v10 plus accepted patches `0_10_1` through `0_10_6`. It does not promote a new stable rollback baseline.

Main update:

- AI Mode gains a `Records & snaps` panel for shared recording/snapshot folder refresh, zip download, and safe delete.
- `pisd/web/static/js/recording_download_panel.js` owns the reusable browser-side recording download/delete behaviour.
- `pisd/web/static/js/global_space_stop.js` owns the global Space STOP shortcut across PiSD pages.
- On AI Mode, Space sends `/api/ai/stop` and `/api/control/stop`; on other pages, Space sends `/api/control/stop`.
- Manual Drive and AI Mode reset local pad/keyboard readouts from the shared `pisd:space-stop` event.

Rollback safety: preserves all accepted 0.10.6 Manual pad behaviour, AI correction math, fixed-throttle safety, `r`/`s` recording shortcuts, and the one-button live workflow.
