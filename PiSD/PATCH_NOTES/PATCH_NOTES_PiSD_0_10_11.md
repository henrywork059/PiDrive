# PiSD 0.10.11 Patch Notes

## Request summary

The user reported that AI Mode contains too much descriptive text and that the safety/motor area should only require one confirmation. The requested UI change was:

- shorten the AI Mode descriptive text;
- replace the separate safety acknowledgement and motor-output checkbox with one confirmation control.

This patch builds forward from the uploaded `PiSD_0_10_0.zip` v10 baseline plus accepted patches `0_10_1` through `0_10_10`.

## Baseline and anti-rollback source

Checked against the latest current state and the previous accepted patch notes (`0_10_8`, `0_10_9`, and `0_10_10`) so this patch does not roll back:

- `0_10_8` AI Mode max-throttle persistence and dirty-field protection;
- `0_10_9` preview buttons above the camera/preview image;
- `0_10_10` restored original recording frame-id / filename format;
- AI Mode `Limiter / correction / manual` three-pane panel;
- one-button `Start live` workflow;
- AI Mode `r` recording and `s` snapshot shortcuts;
- global Space STOP;
- Records & snaps download/delete panel;
- additive correction equation: `AI + manual * Correction %`;
- fixed-throttle-after-correction behaviour;
- Manual pad takeover path through `/api/control/manual`.

## Cause / root cause

The AI Mode page had two usability issues:

1. Several help paragraphs repeated implementation details already covered by documentation and patch notes. This made the live control page visually crowded.
2. The shared drive controls exposed two separate checkboxes:
   - safety acknowledgement;
   - enable motor output.

The backend still needs both guard values, but the user only needs one visible confirmation before allowing motor output from AI Mode.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_11.md`

## Exact behavior changed

### AI Mode text is shorter

The top AI Mode summary is now:

```text
Load a model, start live, then preview or drive.
```

Other AI Mode notes were shortened in the model, limiter, correction, manual pad, run readout, and recordings panels.

### AI Mode has one visible confirmation

The old two-checkbox area:

```text
I confirm the car is safe to test and wheels can be lifted.
Enable motor output
```

is replaced by one checkbox:

```text
Confirm safe test + enable motors
```

The checkbox remains outside the toggled Limiter / Correction / Manual pad panes, so it stays visible in all three AI output modes.

### Backend safety semantics are preserved

The browser now maps the one visible confirmation to both backend guard fields when starting AI:

```json
{
  "safety_ack": true,
  "enable_motor_output": true
}
```

when the checkbox is ticked.

If the checkbox is not ticked, both values are false.

The full Manual pad also uses the same single visible confirmation before sending direct `/api/control/manual` commands.

## Verification actually performed

Performed locally after applying this patch on top of:

```text
PiSD_0_10_0 + 0_10_1 + 0_10_2 + 0_10_3 + 0_10_4 + 0_10_5 + 0_10_6 + 0_10_7 + 0_10_8 + 0_10_9 + 0_10_10
```

Commands run:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Results:

- Python compile check passed.
- AI Mode JavaScript syntax check passed.
- AI Mode static source contract passed.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned `PISD-OK-000` in simulation mode.

## Known limits / next steps

Not hardware-verified in this container:

- real Pi browser rendering of the shortened AI Mode page;
- real single-confirmation behaviour in Chromium;
- real motor-output enable/disable behaviour;
- real AI preview/drive with camera and model loaded;
- real recording/snapshot files.

Full Flask route/API validation was not run because Flask is not installed in this packaging container.
