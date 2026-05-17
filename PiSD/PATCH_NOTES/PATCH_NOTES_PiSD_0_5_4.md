# PATCH NOTES — PiSD_0_5_4

## Request summary

Reuse or modify the current Manual Drive preview panel for AI Mode, and add an overlay driven by the AI model output.

## Cause / root cause

`PiSD_0_5_3` made AI Mode visually closer to Manual Drive, but the preview itself still used a separate simple `ai-preview-box` layout. That meant AI Mode did not benefit from the mature Manual Drive preview frame, overlay visual language, or predicted-path style.

AI Mode also showed raw/safe prediction values in readout boxes only. It did not yet visualize how the AI model output would move the car on top of the camera preview.

## Files changed

- `README.md`
- `docs/ERROR_CODES.md`
- `pisd/__init__.py`
- `pisd/web/templates/ai_mode.html`
- `pisd/web/static/css/ai_mode.css`
- `pisd/web/static/js/ai_mode.js`
- `scripts/test_ai_mode_page.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_4.md`

## Exact behavior changed

### AI preview panel

- Replaced the separate AI preview box with a Manual Drive-style preview frame.
- The AI preview now uses the same core classes as Manual Drive:
  - `mdrv-preview-frame`
  - `mdrv-drive-overlay`
  - `mdrv-overlay-hud`
  - `mdrv-overlay-road`
  - `mdrv-overlay-meter`
  - `mdrv-overlay-wheel-row`
- Added a visible **Overlay: On / Overlay: Off** button directly in the AI preview panel header.
- The AI preview still supports:
  - Start camera
  - Snapshot
  - Live stream
  - Stop camera

### AI model overlay

- Added an AI safe-path overlay on the preview frame.
- The path is drawn from `last_safe_command.steering` and `last_safe_command.throttle`, so it reflects the command after the AI safety limiter, not unfiltered raw model output.
- The overlay also displays the raw model steering/throttle beside the safe command, so the user can compare:
  - raw AI prediction
  - safe limited command
  - left/right motor output
- The overlay reuses the sampled constant-curvature path style from Manual Drive:
  - throttle controls visible path length;
  - steering controls curvature;
  - reverse commands are dashed;
  - stopped/idle commands fade to a neutral guide.

### AI preview state

- Preview starts idle with a clear placeholder image.
- Live stream caption now explains that the overlay is AI-command based.
- Snapshot caption reminds the user to run AI preview or predict once to update the model overlay.
- AI overlay source is tracked as:
  - `ai-stopped`
  - `ai-ready`
  - `ai-preview`
  - `ai-drive`

## Compatibility / safety notes

- This patch does not change AI safety limits or motor-output rules.
- AI drive is still blocked unless the model is runnable, safety acknowledgement is checked, and AI motor output is enabled.
- The overlay is visual only; it does not send motor commands.
- The overlay uses the safe AI command after the limiter to avoid showing an unsafe raw path as the primary predicted movement.
- Raw AI steering/throttle are still displayed as reference values.

## Verification performed

Performed locally after applying the latest `0_5_3` state over `PiSD_0_5_0`:

- `python3 -m compileall -q pisd scripts` — passed.
- `node --check pisd/web/static/js/ai_mode.js` — passed.
- `python3 scripts/test_ai_mode_page.py --static-only` — passed.
- `python3 scripts/test_manual_drive_page.py --static-only` — passed.
- `python3 scripts/test_front_page_tabs.py --static-only` — passed.
- `python3 scripts/test_ai_drive_service.py` — passed.
- `python3 scripts/test_settings_persistence.py` — passed.
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui` — passed.

## Not verified

- Real Raspberry Pi camera/motor hardware behavior was not tested here.
- Real `.tflite` / `.keras` model inference was not tested here.
- Full Flask route checks were not completed here because Flask is not installed in this container.

## Known limits / next steps

- The AI overlay currently uses fixed visual calibration values. A future patch could expose the same overlay calibration controls used by Manual Drive.
- A future patch should add model-confidence / inference-age indicators when real model inference is being tested.
- A future patch should add a preview-only live inference loop that runs without motor output so model behaviour can be checked safely before driving.
