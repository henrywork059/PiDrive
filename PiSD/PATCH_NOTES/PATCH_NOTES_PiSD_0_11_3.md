# PiSD 0.11.3 Patch Notes

## Request summary
- Move **Confirm safe test + enable motors** to the **top right** of the AI workflow panel.
- Place it **to the left of the Settings button**.

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with the accepted `PiSD_0_11_1_patch.zip` and `PiSD_0_11_2_patch.zip` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_2.md`
  - `PATCH_NOTES_PiSD_0_11_1.md`
  - `PATCH_NOTES_PiSD_0_11_0.md`
  - `PATCH_NOTES_PiSD_0_10_11.md`
- Preserved the 0.11.2 AI workflow settings popup, top-panel camera FPS control, and manual-pad-release preview fix.
- Preserved the 0.11.1 AI preview/manual separation, AI-safe recording labels, and yellow preparatory buttons.
- Preserved the 0.11.0 single confirmation semantics.

## Cause / root cause
- In 0.11.2, the confirmation checkbox was moved into the top AI workflow panel, but it remained under the panel summary rather than inside the panel-header action row.
- That placement did not match the requested workflow emphasis and made the safety confirmation feel visually detached from the top-right control cluster.

## Files changed
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_3.md`

## Exact behavior changed
- The `Confirm safe test + enable motors` control now sits in the top-right action row of the **AI workflow / Model-based driving** panel.
- The action-row order is now:
  1. `Confirm safe test + enable motors`
  2. `Settings`
  3. `PISD-OK-000`
- The confirmation keeps the same `aiEnableMotor` ID and still drives the same safety logic, so backend behavior is unchanged.
- On narrow screens, the control cluster can still wrap, and the confirmation label can wrap normally to avoid overflow.

## Compatibility / migration notes
- No config schema change.
- No API change.
- No change to AI preview, manual override, recording labels, camera FPS settings, or motor safety semantics.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

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
- AI Mode static/source contract check passed.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned OK status in this container.

## Known limits / next steps
- Real browser rendering on the Pi was not tested in this container.
- On the Pi, confirm the top-right layout looks correct at your target display width.
