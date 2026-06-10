# PiSD 0.11.1 Patch Notes

## Request summary
- Keep **Start AI preview** running when the AI page manual drag/manual pad mode is selected.
- In manual drag mode, keep the AI preview overlay on the camera frame while manual input owns the motors.
- When AI Mode Snapshot or Record is used, save the AI output as the trainer label instead of the manual motor command.
- Make **Start AI preview**, **Snapshot**, and **Record** yellow preparatory action buttons.

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_0.md`
  - `PATCH_NOTES_PiSD_0_10_11.md`
  - `PATCH_NOTES_PiSD_0_10_10.md`
  - `PATCH_NOTES_PiSD_0_10_9.md`
- Preserved the 0.11.0 single safety/motor confirmation wording and AI text cleanup.
- Preserved the 0.10.9 control placement above the preview.
- Preserved the 0.10.10 original frame-id format.
- Preserved the 0.10.11 AI output correction and max-throttle persistence behavior.

## Cause / root cause
- The manual control API route always called `ai_drive_service.stop(..., stop_motors=False)` before applying manual motor commands.
- That was correct for full AI drive takeover, but it also stopped the AI preview loop, so manual drag mode could not keep the model overlay and latest AI output alive.
- Recording labels previously used the current motor/manual command by default, so AI Mode manual-overlay recording could save the manual command instead of the AI model output.

## Files changed
- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/services/ai_drive_service.py`
- `pisd/services/recording_service.py`
- `pisd/services/ai_correction.py`
- `pisd/services/ai_safety.py`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/static/css/ai_mode.css`
- `scripts/test_ai_mode_page.py`
- `scripts/test_recording_service.py`
- `README.md`
- `docs/STABLE_BASELINE.md`
- `docs/TEST_PLAN.md`
- `docs/RECORDING_DATA.md`
- `docs/AI_MODE_CODE_MAP.md`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_11_1.md`

## Exact behavior changed
- `/api/control/manual` no longer fully stops the AI service.
- Manual control now calls `ai_drive_service.keep_preview_for_manual_override(...)`:
  - if AI was driving, it is demoted to preview mode;
  - if AI preview was already running, it keeps running;
  - motor output from AI is disabled;
  - manual input is then applied to the motors.
- The AI runtime loop now checks whether drive output is still allowed on every loop iteration.
- `predict_once(...)` also re-checks the drive gate immediately before motor output, so a manual override that happens during model inference cannot be overwritten by a late AI motor update.
- AI page manual pad status now states that the AI preview overlay can keep running while manual input owns the motors.
- AI Mode Snapshot now sends `command_source: "ai_safe_command"`.
- AI Mode Record now sends `command_source: "ai_safe_command"`.
- Recording service now supports `manual_command` and `ai_safe_command` label sources:
  - manual/default recordings still label from the manual motor command;
  - AI Mode recordings label `steering` and `throttle` from the latest AI safe output;
  - full `records.jsonl` keeps `manual_command`, `motor_state`, `control_label_source`, and `ai_output` for traceability;
  - trainer-friendly `labels.jsonl` also includes `control_label_source` and `ai_output`.
- `Start AI preview`, `Snapshot`, and `Record` buttons in AI Mode now use yellow/amber styling.
- Added small `ai_correction.py` and `ai_safety.py` helper modules because the current validation scripts reference those helper contracts.

## Compatibility / migration notes
- Existing manual recordings remain compatible and continue using manual motor labels by default.
- Existing AI Mode recordings are not modified.
- New AI Mode recordings include extra trace fields. Trainers that only read `frame`, `steering`, and `throttle` can keep working because those fields are still present.
- The patch does not change motor calibration, camera settings, model loading paths, frame-id format, or the single AI safety confirmation requirement.

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
- Hardware motor and camera behavior were not tested in this container.
- On the Pi, confirm this workflow:
  1. start AI preview;
  2. switch to manual drag/manual pad mode;
  3. verify the AI overlay continues updating;
  4. verify manual drag controls the motors;
  5. take Snapshot or Record and confirm `labels.jsonl` uses `control_label_source: "ai_safe_command"` with AI safe output values.
