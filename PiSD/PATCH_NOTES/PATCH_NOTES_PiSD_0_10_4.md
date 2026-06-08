# PiSD 0.10.4 Patch Notes

## Request summary

Build forward from `PiSD_0_10_0` plus accepted patches `0_10_1`, `0_10_2`, and `0_10_3`.

Requested correction:

- AI Mode correction should not replace part of the AI value.
- The AI value should remain the base command.
- The manual correction value should be multiplied by the user percentage and then added to the AI value.

## Cause / root cause

`0.10.3` implemented the correction pane as a replacement-style weighted blend:

```text
corrected = AI * (1 - percent) + manual * percent
```

That made a higher manual percentage reduce the original AI output. This did not match the intended correction workflow, where the user correction is an additive adjustment on top of the AI prediction.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_4.md`

## Behaviour changed

### Additive AI correction equation

AI Mode correction now uses the AI prediction as the base value:

```text
correction_gain = Correction % / 100

corrected steering = clamp(ai steering + manual steering * correction_gain, -1, 1)
corrected throttle = clamp(ai throttle + manual throttle * correction_gain, -1, 1)
```

Examples:

```text
ai steering = +0.40
manual steering = -0.60
Correction % = 50

corrected steering = +0.40 + (-0.60 * 0.50)
corrected steering = +0.10
```

```text
ai steering = +0.30
manual steering = +0.40
Correction % = 100

corrected steering = +0.70
```

So 100% correction means "add the full manual correction", not "replace AI with manual".

### Safety path preserved

The corrected command is still passed through the existing safety limiter after correction.

In `AI steering + fixed throttle` mode, the throttle correction is still ignored by the safety layer because the fixed-throttle value is enforced after correction. Manual steering correction still applies.

### UI wording clarified

The correction pane now uses clearer additive wording:

- `Manual mix %` was renamed to `Correction %`.
- The readout now says `Corrected steering` and `Corrected throttle`.
- Help text now says the manual correction is added to AI output by the correction percentage.

The internal saved config key remains `manual_mix_percent` for backward compatibility with existing saved settings and the `0.10.3` API contract.

### Status compatibility

The previous `last_mixed_command` field remains available for compatibility. `last_corrected_command` was added as a clearer alias for the additive corrected command before the safety limiter.

## Preserved behaviour / rollback safety

Checked against the current code state and previous accepted patch notes:

- `0_10_3`: AI Mode correction pane, drag pad, arrow-key correction, `s` snapshot shortcut, `r` record shortcut, green AI snapshot/record buttons, and fixed-throttle protection are preserved.
- `0_10_2`: green Manual Drive / AI Mode front-page cards, shortened labels, and removal of AI `Refresh frame` are preserved.
- `0_10_1`: one-button `Start live` workflow and Manual Drive `r` / `s` shortcuts are preserved.
- `0_10_0`: v10 baseline runtime, AI model loading, recording, overlay, and config safety behaviours are preserved.

This patch does not change camera setup, motor mapping, recording folder format, overlay geometry, model-loading backend order, or the persistent config schema.

## Verification actually performed

Performed locally in the patched `PiSD` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

`test_ai_mode_page.py --static-only` now includes deterministic backend equation checks confirming:

- 50% correction uses `AI + manual * 0.5`.
- 100% correction adds the full manual correction to the AI base.
- corrected commands are clamped to `[-1, 1]` before the existing safety limiter.

The patch was also applied over a clean `PiSD_0_10_0` extraction with `PiSD_0_10_1_patch.zip`, `PiSD_0_10_2_patch.zip`, and `PiSD_0_10_3_patch.zip`, then the same safe checks were re-run.

## Not verified here

The following require the real Raspberry Pi/browser/hardware environment:

- Real Pi camera live preview.
- Browser keyboard shortcut behaviour in Chromium on the Pi.
- Real snapshot/record files.
- Real motor output.
- Real AI model inference through an installed TFLite/TensorFlow backend.

The non-static Flask/API route test was not run here because it depends on the full PiSD Python environment. On the Pi or a development venv with dependencies installed, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_ai_mode_page.py
```

## Suggested Pi-side check

After applying this patch on the Pi:

1. Hard refresh `/ai-mode`.
2. Open `Limiter / correction` → `Correction`.
3. Confirm the slider label is `Correction %`.
4. Check that the readout says `Corrected steering` / `Corrected throttle`.
5. At 50%, confirm manual correction changes the AI command by half of the manual value.
6. At 100%, confirm manual correction adds fully to the AI value instead of replacing it.
7. Confirm fixed-throttle mode still keeps throttle fixed while steering correction remains active.
