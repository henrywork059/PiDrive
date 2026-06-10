# PiSD 0.11.5 Patch Notes

## Request summary
- Add a new panel under the AI action log for the latest/recent error log.
- Fix the camera restart bug where turning the camera off could make the next start fall back to simulation frames.
- Add a fourth AI output tab: **AI assist**.
- In AI assist mode, provide a manual driving pad where the user drives normally, while AI model steering multiplied by a percentage is added to the user's steering input only.

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with accepted patches `0_11_1`, `0_11_2`, `0_11_3`, and `0_11_4` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_4.md`
  - `PATCH_NOTES_PiSD_0_11_3.md`
  - `PATCH_NOTES_PiSD_0_11_2.md`
  - `PATCH_NOTES_PiSD_0_11_1.md`
- Preserved the 0.11.4 global settings behavior, including shared `manual_drive.speed` and global `camera.fps`.
- Preserved the 0.11.3 top-right safety confirmation layout.
- Preserved the 0.11.2 AI workflow Settings popup and manual-pad-release preview fix.
- Preserved the 0.11.1 AI preview/manual separation and AI-safe recording label behavior.

## Cause / root cause
- The AI page had only the action log. Backend component error histories already existed, but the AI workflow did not show them directly under the AI log.
- Camera stop/start reused the same stop event object for each capture thread. If the browser restarted the camera before the old capture thread fully exited, clearing that shared event could let the stale thread continue and interfere with the new camera start. That could make the hardware open path fail and force the service into simulation.
- The existing Correction pane supported `AI + manual × %`. The requested new mode needs the opposite driving role: the user owns manual throttle and steering, while AI contributes steering assist only.

## Files changed
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_5.md`

## Exact behavior changed

### Last error log panel
- Added a **Last error log / Recent errors** panel under the AI action log.
- The panel shows recent errors from app, camera, motor, settings, recording, and AI mode error reporters.
- `/api/ai/status` now also returns `errors`, so the panel refreshes during normal AI status updates.
- Added a **Refresh errors** button that calls the existing `/api/errors` endpoint.

### Camera restart robustness
- Each camera start now creates a fresh stop event for its capture thread.
- Stop now leaves the old thread's event set instead of reusing and clearing it for the next start.
- Start cleans up any stale Picamera2 object before opening hardware again.
- Stop clears the cached latest JPEG/raw frame so an old simulation frame is not reused after restarting.

### AI assist tab
- The output pane now has four tabs:
  1. Limiter
  2. Correction
  3. Manual pad
  4. AI assist
- AI assist provides its own manual pad and readout.
- AI assist output uses:

```text
output steering = manual steering + AI model steering × Assist %
output throttle = manual throttle
```

- Steering is clamped to `[-1, 1]` before sending to the guarded Manual Drive endpoint.
- AI assist does not create a separate similar percent setting. It reuses the same global AI `manual_mix_percent` value as Correction %, so there is still one saved percentage source of truth.
- AI assist uses the existing global Manual Drive speed setting for throttle range.
- AI assist keeps the AI preview overlay alive and sends motor commands through `/api/control/manual`, so the existing manual override protection still prevents AI drive from fighting manual control.

### Version line
- Updated `pisd/__init__.py` to `0.11.5`.

## Compatibility / migration notes
- No config schema change is required.
- Existing saved global settings remain compatible.
- Existing AI Correction behavior is unchanged.
- Existing Manual pad behavior is unchanged.
- Existing AI recording behavior is unchanged; AI Mode recording still uses `command_source: "ai_safe_command"`.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Additional direct camera restart smoke check was run in simulation mode:

```bash
python3 - <<'PY'
from pisd.services.camera_service import CameraService
from pisd.app import load_defaults
cam = CameraService((load_defaults().get('camera') or {}), hardware_enabled=False)
for i in range(2):
    ok, msg = cam.start()
    assert ok, msg
    frame, seq, *_ = cam.wait_for_jpeg_frame(timeout=1.0)
    assert frame is not None, 'no frame after restart'
    ok, msg = cam.stop()
    assert ok, msg
print('camera restart smoke OK')
PY
```

Results:
- Python compile check passed.
- AI Mode JavaScript syntax check passed.
- AI Mode static/source contract passed with AI assist and last error log tokens.
- Settings persistence checks passed.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned OK status in simulation mode.
- Camera start/stop/start simulation smoke check passed.

## Known limits / next steps
- Real Picamera2 hardware restart was not tested in this container.
- Real browser pointer testing for the new AI assist pad was not hardware-tested here.
- On the Pi, confirm this workflow:
  1. Start live.
  2. Stop camera.
  3. Start live again and verify it returns to Picamera2 instead of simulation.
  4. Load model and start AI preview.
  5. Open **AI assist**, tick confirmation, drive with the pad, and confirm steering equals manual steering plus AI steering assist while throttle stays manual.
