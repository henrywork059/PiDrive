# PiSD 0.9.10 Patch Notes

## Request summary

This patch updates AI Mode after testing showed that the AI deployment/inference speed was acceptable, but the car control update rate appeared slower than the configured AI update value. The user also requested AI Mode layout/control updates:

- increase the allowed maximum AI update Hz
- check why the AI control update speed did not appear to follow the setting
- place `Start AI preview`, `Start AI drive`, and `Stop AI` beside the camera / AI prediction preview
- add recording and saved-snapshot buttons to AI Mode
- combine the separate `Start camera` and `Live stream` controls

## Cause / root cause

The AI loop previously waited for a *newer* camera frame on every prediction. That meant control updates could be limited by camera frame delivery or by wait/retry timing, even when TFLite inference itself was fast. In practice, the Update Hz setting could therefore feel like it was not controlling motor-command refresh speed.

The UI also had separate camera-start and live-stream buttons, while AI run controls lived in a separate Run panel away from the preview. The existing AI page had no direct recording/snapshot controls even though the shared recording service already supported the needed backend API.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/scripts/test_ai_drive_service.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_10.md`

## Behaviour changed

### AI control update loop

- AI Mode now uses the latest cached camera frame immediately when one is available.
- The loop only waits when no frame has arrived yet.
- This decouples motor-command refresh from the requirement that every inference must wait for a newer camera frame.
- The configured AI update rate should now more directly control the intended command refresh loop, subject to actual model inference time and Pi CPU limits.

### AI Update Hz range

- The AI `update_hz` setting now supports up to `60` Hz.
- Backend setting normalisation now clamps `update_hz` to `1.0 .. 60.0`.
- Frontend slider maximum is now `60`.
- Default AI update rate is now `12` Hz.

### AI Mode preview controls

- `Start camera` and `Live stream` were combined into one button: `Start camera + live stream`.
- `Start AI preview`, `Start AI drive`, and `Stop AI` were moved into the camera / AI prediction preview panel.
- The old Run panel now focuses on readouts/status and points users back to the preview buttons.

### AI Mode recording and snapshots

- Added `Save snapshot` button to AI Mode.
- Added `Start recording` / `Stop recording` toggle to AI Mode.
- Added `REC on/off` indicator to AI Mode.
- AI Mode uses the shared recording API:
  - `POST /api/recording/capture`
  - `POST /api/recording/start`
  - `POST /api/recording/stop`
- AI recording sessions use label `ai_mode`.
- AI saved snapshots use label `ai_mode_capture`.
- Recording FPS is started from the AI Update Hz value, capped by the existing recording service safety range.

### AI status API

- `/api/ai/status` now also returns `recording` status so the AI page can keep its REC indicator in sync.

## Preserved behaviour / rollback safety

This patch keeps the accepted behaviours from earlier v9 patches:

- linear X steering remains unchanged
- keyboard steering still ramps/recentres over `0.8 s`
- removed motor dead-zone/start-kick code remains removed
- intended motor output display remains positive for forward vehicle intent
- AI model upload/delete and TFLite runtime diagnostics remain intact
- TFLite shape/dequantisation fixes remain intact
- AI camera warm-up reliability improvements remain intact
- overlay calibration and recording/snapshot overlay sidecars remain intact

## Verification actually performed

Applied over the current `PiSD_0_9_9` state and ran:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_ai_drive_service.py
python3 scripts/test_recording_service.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed checks passed in this container.

## Not verified here

- Real Raspberry Pi camera frame timing was not measured here.
- Real TFLite model inference speed on the Pi was not measured here.
- Real motor output timing was not measured here.
- Full Flask route tests were not run here because this environment is not the target Pi runtime.

## Next recommended on-Pi check

After applying the patch and restarting PiSD:

1. Open AI Mode.
2. Start camera + live stream.
3. Load the model.
4. Set Update Hz to a test value such as `20`, `30`, or `40`.
5. Start AI preview.
6. Watch `Loop` and `Frame seq`:
   - `Loop` should track the AI control loop as closely as the Pi/model can manage.
   - `Frame seq` may increase at the camera FPS, which can be lower than the AI loop because cached frames may be reused between new camera frames.
7. With wheels lifted, start AI drive and check whether left/right intended outputs refresh smoothly.
