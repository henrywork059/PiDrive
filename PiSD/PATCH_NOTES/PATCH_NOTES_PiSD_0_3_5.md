# PiSD 0.3.5 Patch Notes

## Request summary

Improve the Manual Drive and overall page/panel presentation after the 0.3.1-0.3.4 layout regressions, fix the drag-pad pointer/knob mismatch, keep manual speed below 1.0, and add frame capture/recording with traceable metadata.

## Cause / root cause

- Presentation rules had accumulated across page-specific CSS, `unified_layout.css`, and the design-system layer. This made it possible for saved panel settings or older CSS to move Manual Drive panels into the wrong regions.
- The drag-pad knob used percentage translations inside `transform`; CSS transform percentages are relative to the knob, not the pad, so the knob could appear offset from the pointer.
- Manual-drive and motor max-speed controls allowed values up to `1.0`, which is too high for the current safe testing workflow.
- Snapshot display and actual saved capture were not separated. The UI could show a snapshot frame but did not create a traceable dataset record beside the image.

## Files changed

- `README.md`
- `config/defaults.json`
- `docs/ERROR_CODES.md`
- `docs/PRESENTATION_DEVELOPMENT.md`
- `docs/RECORDING_DATA.md`
- `docs/TEST_PLAN.md`
- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/core/errors.py`
- `pisd/core/presentation_registry.py`
- `pisd/core/settings_manager.py`
- `pisd/services/motor_service.py`
- `pisd/services/recording_service.py`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/templates/settings_tab.html`
- `pisd/web/templates/testing_server.html`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/css/pisd_design_system.css`
- `pisd/web/static/js/manual_drive.js`
- `scripts/test_manual_drive_page.py`
- `scripts/test_recording_service.py`
- `scripts/test_ui_presentation_consistency.py`

## Behaviour changed

### Manual Drive layout

The intended PC/iPad Manual Drive grid is now:

```text
status  drive
preview drive
preview stop
log     log
```

This keeps the camera panel directly under the status panel, while placing Manual Control in the right-side control column. On phone/narrow screens the order becomes status, preview, drive, stop, log.

### Drag pad

The drag knob now uses parent-relative `left/top` variables:

```text
--knob-left
--knob-top
```

This fixes the knob position so it matches the pointer more closely.

### Speed limits

Manual drive speed and motor max-speed settings are capped at `0.65` instead of allowing `1.0` as the normal UI/service limit.

### Capture and recording

Manual Drive now includes:

- `Capture frame` — saves one frame and JSONL metadata record.
- `Record` — starts/stops ordered frame recording.

New API endpoints:

```text
GET  /api/recording/status
POST /api/recording/capture
POST /api/recording/start
POST /api/recording/stop
```

Saved output goes under `PiSD/recordings/` using day/session folders. Each frame has a unique ID, ordered index, timestamp, camera settings, steering/throttle, motor outputs, bias, directions, and max-speed tuning data.

### Error codes added

- `PISD-REC-001` to `PISD-REC-007`
- `PISD-TEST-022`

## Verification performed

Executed locally in simulation/static mode:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

All listed checks passed.

## Not verified here

- Real Raspberry Pi browser rendering.
- Real camera capture through `/api/recording/capture` on the Pi.
- Long recording sessions on the Pi SD card.
- Real motor output while recording.

## Known limits / next steps

- The recording thread saves JPEGs and JSONL metadata; it does not yet provide a GUI file browser for recorded sessions.
- Recording defaults to a modest FPS to avoid overwhelming the Pi/SD card. Tune recording FPS from the backend/UI later after SD card write performance is known.
- If the browser still shows old CSS, hard-refresh or open a private window because earlier pages used cached CSS aggressively.
