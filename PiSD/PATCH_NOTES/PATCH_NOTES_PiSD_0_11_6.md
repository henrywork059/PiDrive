# PiSD 0.11.6 Patch Notes

## Request summary
- Replace the single Camera FPS concept with three independent global rates:
  - **Camera capture FPS**: real camera frame capture rate.
  - **Live preview FPS**: browser MJPEG upload rate only.
  - **AI prediction FPS**: model inference rate.
- Keep the rule that live preview/upload FPS must not control AI driving performance.
- Use recommended defaults for Pi 4:
  - Camera capture FPS: `30`
  - Live preview FPS: `20`
  - AI prediction FPS: `20`

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with accepted patches `0_11_1` through `0_11_5` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_5.md`
  - `PATCH_NOTES_PiSD_0_11_4.md`
  - `PATCH_NOTES_PiSD_0_11_3.md`
  - `PATCH_NOTES_PiSD_0_11_2.md`
- Preserved the 0.11.5 Last error log panel, camera stop/start restart fix, and AI assist tab.
- Preserved the 0.11.4 global/shared settings source-of-truth behavior and Manual speed default `0.80`.
- Preserved the 0.11.3 safety confirmation placement.
- Preserved the 0.11.2 AI preview/manual-pad-release separation.

## Cause / root cause
- Earlier UI and settings used a single Camera FPS value for too many different jobs.
- That made it easy to confuse camera capture rate, browser upload/network load, and AI model inference rate.
- The AI loop already read the latest camera frame buffer, but it did not expose frame-reuse state clearly and still treated the user-facing rate as a generic update Hz.

## Files changed
- `PiSD/config/defaults.json`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_6.md`

## Exact behavior changed

### Global rate settings
- `camera.fps` is now treated as **Camera capture FPS**.
- New global setting `camera.live_preview_fps` controls only `/video_feed` browser upload throttling.
- `ai_mode.update_hz` is now presented as **AI prediction FPS**.
- Defaults are now:
  - `camera.fps = 30`
  - `camera.live_preview_fps = 20`
  - `ai_mode.update_hz = 20`

### AI workflow popup
- The AI workflow Settings popup now exposes:
  - Camera capture FPS
  - Live preview FPS
  - AI prediction FPS
- Applying from the popup uses `/api/settings/apply`, so values save to the shared backend settings file and apply globally.
- The popup no longer saves a page-only Camera FPS value.

### Settings page
- The main Settings page now exposes the same global three-rate settings.
- Camera settings includes Camera capture FPS and Live preview FPS.
- A new AI rate settings card exposes AI prediction FPS.

### Live preview separation
- `/video_feed` now reads `camera.live_preview_fps` from global settings and throttles browser MJPEG upload to that rate.
- This does not change camera capture FPS and does not change AI prediction FPS.

### AI prediction loop
- AI prediction rate defaults to 20 Hz.
- The AI loop tracks the latest camera frame sequence used for inference.
- If the camera frame ID has not changed since the last inference, the model is not run again on the same frame; PiSD reuses the latest AI raw prediction and records this in AI status:
  - `last_inference_frame_seq`
  - `last_prediction_reused`
  - `prediction_reuse_count`
- Manual correction, limiter/safety, motor output, and AI assist behavior remain active on top of the latest prediction state.

## Compatibility / migration notes
- Existing saved `camera.fps` values are preserved and become Camera capture FPS.
- Existing saved `ai_mode.update_hz` values are preserved and become AI prediction FPS.
- Existing configs missing `camera.live_preview_fps` safely receive the default `20` on settings normalization.
- No recording format change.
- No motor config change.
- No change to the AI assist tab behavior from 0.11.5.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/settings_tab.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Results:
- Python compile check passed.
- AI Mode JavaScript syntax check passed.
- Settings page JavaScript syntax check passed.
- AI Mode static/source contract passed.
- Settings persistence/global settings checks passed, including three-rate clamp checks.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned OK status in simulation mode and reported camera defaults `fps=30`, `live_preview_fps=20`, `target_capture_fps=30`, and `target_live_preview_fps=20`.

## Known limits / next steps
- Real Pi camera hardware capture-rate behavior was not tested in this container.
- Browser MJPEG network upload rate should be confirmed on the Pi by setting Live preview FPS low while keeping AI prediction FPS higher.
- Real AI inference performance still depends on model size and installed runtime.
