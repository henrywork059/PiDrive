# PiSD 0.11.2 Patch Notes

## Request summary
- Add a **Settings** button to the top AI workflow / Model-based driving panel.
- Open an overlay popup from that button so the user can set **Camera FPS**.
- Move **Confirm safe test + enable motors** into the top AI workflow panel.
- Fix the AI Mode Manual pad release bug where releasing the pad stopped the AI overlay/preview.

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with the accepted `PiSD_0_11_1_patch.zip` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_1.md`
  - `PATCH_NOTES_PiSD_0_11_0.md`
  - `PATCH_NOTES_PiSD_0_10_11.md`
  - `PATCH_NOTES_PiSD_0_10_10.md`
- Preserved the 0.11.1 AI preview/manual separation, AI-safe recording labels, yellow Start AI preview/Snapshot/Record styling, and manual override race protection.
- Preserved the 0.11.0 single confirmation semantics.
- Preserved the 0.10.10 restored original frame-id format.
- Preserved top-of-preview camera/run/record controls and global Space STOP behavior.

## Cause / root cause
- The AI Mode Manual pad release path called `/api/control/stop`, and that backend route always stopped the AI drive service as well as the motors.
- That was correct for global STOP, but too broad for Manual pad release because manual release only needs to zero motor output while the AI preview loop should continue overlaying model predictions.
- The AI workflow settings request needed a small page-level popup because the existing camera settings API already supports applying FPS; the missing piece was a direct AI workflow control.

## Files changed
- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/web/templates/ai_mode.html`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/ai_mode.css`
- `scripts/test_ai_mode_page.py`
- `README.md`
- `docs/STABLE_BASELINE.md`
- `docs/TEST_PLAN.md`
- `docs/AI_MODE_CODE_MAP.md`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_11_2.md`

## Exact behavior changed
- The `Confirm safe test + enable motors` checkbox moved from the Limiter / Correction / Manual panel into the top AI workflow panel.
- The checkbox keeps the same `aiEnableMotor` ID, so existing AI drive/manual safety logic still maps it to both backend guard values:
  - `safety_ack`
  - `enable_motor_output`
- The AI workflow panel now has a **Settings** button.
- The Settings popup includes a **Camera FPS** number input and an **Apply camera FPS** button.
- The popup loads current camera FPS from `GET /api/camera/config`.
- Applying the popup sends `POST /api/camera/apply` with the selected FPS, using the existing camera-service restart and persistence path.
- `/api/control/stop` now accepts an optional JSON flag:
  - `keep_ai_preview: true`
- When that flag is present, the backend stops only the motors and returns the current AI status without stopping the AI preview service.
- AI Mode Manual pad release now sends `/api/control/stop` with `keep_ai_preview: true`.
- Manual pad release status now says the AI preview was kept when the AI preview loop is still running.
- Global STOP, `STOP AI + motors`, page-hide cleanup, and normal `/api/control/stop` calls without the flag still stop AI and motors normally.

## Compatibility / migration notes
- No runtime config schema change is required.
- Existing camera settings remain compatible.
- Existing AI Mode settings remain compatible.
- Existing recordings and labels are not modified.
- The camera FPS popup uses the existing `camera.fps` setting, so values saved through the popup are shared with the rest of PiSD camera behavior.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

The full `python3 scripts/test_ai_mode_page.py` was also attempted. The static/source/helper checks passed, but Flask route testing could not run in this container because Flask is not installed here:

```text
PISD-APP-002: Flask is not installed. Run: python -m pip install -r requirements.txt
```

## Known limits / next steps
- Hardware camera/motor behavior was not tested in this container.
- On the Pi, confirm this browser workflow:
  1. open `/ai-mode`;
  2. confirm the safety checkbox is in the top AI workflow panel;
  3. click Settings, set Camera FPS, and apply it;
  4. start live, load a model, start AI preview;
  5. switch to Manual pad, drag and release;
  6. confirm motors stop on release but the AI overlay continues updating;
  7. confirm Space STOP and `STOP AI + motors` still stop AI and motors together.
