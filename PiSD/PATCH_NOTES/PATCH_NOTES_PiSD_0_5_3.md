# PATCH NOTES — PiSD_0_5_3

## Request summary

Fix the AI Mode throttle controls so both **Max throttle** and **Fixed throttle** can be set to `1.00`, and restyle AI Mode so it reuses the same panel/button/topbar design language as Manual Drive.

## Cause / root cause

In `PiSD_0_5_2`, AI Mode had three independent limits that all stopped full-scale throttle:

- `pisd/web/templates/ai_mode.html` set the Max throttle slider to `max="0.45"`.
- `pisd/web/templates/ai_mode.html` set the Fixed throttle slider to `max="0.35"`.
- `AIDriveService` and `SettingsManager` also clamped those two values to `0.45` and `0.35` respectively.

This meant changing only the UI would not be enough: saved settings and runtime safety output would still be capped below `1.00`.

The AI page also used its own larger hero/card styling, so it did not visually match the more compact Manual Drive page.

## Files changed

- `README.md`
- `docs/ERROR_CODES.md`
- `pisd/__init__.py`
- `pisd/core/settings_manager.py`
- `pisd/services/ai_drive_service.py`
- `pisd/web/templates/ai_mode.html`
- `pisd/web/static/css/ai_mode.css`
- `pisd/web/static/js/ai_mode.js`
- `scripts/test_ai_drive_service.py`
- `scripts/test_ai_mode_page.py`
- `scripts/run_standard_validation.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_3.md`

## Exact behavior changed

### AI throttle range

- Max throttle can now be set from `0.00` to `1.00`.
- Fixed throttle can now be set from `0.00` to `1.00`.
- The HTML range controls now use `max="1.0"`.
- `AIDriveService.apply_settings(...)` now preserves values up to `1.0`.
- `AIDriveService.apply_safety(...)` now allows the safety limiter to output up to the configured `1.0` max throttle.
- `SettingsManager` now persists valid AI throttle settings up to `1.0` instead of silently clamping them back down.
- `ai_mode.js` enforces the full-scale range at page startup as an extra front-end guard.

### AI page style/layout

- AI Mode now loads `manual_drive.css` and reuses Manual Drive classes such as:
  - `mdrv-topbar`
  - `mdrv-panel`
  - `mdrv-panel-head`
  - `mdrv-button`
  - `mdrv-primary`
  - `mdrv-danger`
  - `mdrv-code`
- The old AI hero layout was replaced with a Manual Drive-style sticky topbar.
- AI panels now use compact Manual Drive-style panel spacing and readout boxes.
- The STOP AI + motors button is now in the topbar, similar to the Manual Drive STOP placement.
- Added an AI workflow intro panel explaining the full-scale throttle range and safety limiter.

## Compatibility / safety notes

- Existing lower throttle settings remain valid and are not reset.
- Values above `1.0` are still clamped to `1.0`.
- The AI safety layer still sits between model output and motor output.
- This patch does not make model inference more aggressive by default; it only allows the user to select a higher safety limit.
- AI drive still requires a runnable model, safety acknowledgement, and motor output enable.

## Verification performed

Performed locally after applying `PiSD_0_5_2_patch` over `PiSD_0_5_0`:

- `python3 -m compileall -q .` — passed.
- `node --check pisd/web/static/js/ai_mode.js` — passed where Node.js was available.
- `python3 scripts/test_ai_drive_service.py` — passed, including a new full-scale throttle check.
- `python3 scripts/test_ai_mode_page.py --static-only` — passed.
- `python3 scripts/test_settings_persistence.py` — passed.
- Manual SettingsManager full-scale AI throttle save/reload snippet — passed.
- `python3 scripts/test_front_page_tabs.py --static-only` — passed.
- `python3 scripts/test_manual_drive_page.py --static-only` — passed.
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui` — passed.

## Not verified

- Real Raspberry Pi motor/camera hardware behavior was not tested here.
- Full Flask route checks were not completed here because Flask is not installed in this container.
- Real `.tflite` / `.keras` model inference was not tested.

## Known limits / next steps

- Full-scale AI throttle can move the car faster; start testing with wheels lifted and low values first.
- A future patch should add visible throttle-risk warnings when Max throttle or Fixed throttle is set above a chosen threshold, for example `0.50`.
- A future patch should add an AI prediction overlay similar to Manual Drive’s predicted path overlay.
