# PiSD 0.10.6 Patch Notes

## Request summary

Add a third AI Mode output-panel toggle for a full manual driving pad.

Also make sure the configuration button is not hidden when the user switches between the output-panel modes. The requested behaviour is that only one configuration/save button is needed, and it should stay outside the toggled pane content.

This patch builds forward from the uploaded `PiSD_0_10_0` v10 baseline plus accepted patches `0_10_1` through `0_10_5`.

## Cause / root cause

Before this patch, the AI Mode safety/output panel had two toggled panes:

- `Limiter`
- `Correction`

The Correction pane was only for additive AI correction. It was not a full manual takeover pad. Also, the live safety controls were inside the Limiter pane, so once the user switched to Correction, the safety acknowledgement and motor-output enable controls were not visible even though other panes might still need them.

The UI needed a clearer separation:

- AI limiter settings;
- AI correction input;
- direct full manual takeover.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/AI_MODE_CODE_MAP.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_6.md`

## Behaviour changed

### Three-way AI output panel

AI Mode now shows:

```text
Limiter / correction / manual
```

The tab strip now has three panes:

```text
Limiter
Correction
Manual pad
```

### Shared safety controls moved outside toggled panes

The safety acknowledgement and motor-output enable controls now sit below the tab strip and outside the three toggled panes.

They stay visible in:

- Limiter;
- Correction;
- Manual pad.

The configuration/save button remains a single button:

```text
Save AI settings
```

It stays in the panel header and is not duplicated inside the toggled panes.

### Full Manual pad added

The new `Manual pad` pane adds a direct Manual Drive-style takeover control inside AI Mode:

- drag pad for steering/throttle;
- arrow-key drive controls;
- manual speed range;
- direct STOP manual button;
- same visible readouts for manual steering and manual throttle.

This is a takeover mode, not AI correction.

It sends direct guarded manual commands through:

```text
POST /api/control/manual
```

That route already stops the AI drive service before applying manual motor output, so manual takeover does not blend with AI prediction.

### Manual pad keyboard controls

When the `Manual pad` pane is active and focus is not inside a text field:

```text
↑ / ↓ = throttle step
hold ← / → = steering ramp
Space = STOP manual
r = record / stop recording
s = snapshot
```

The Correction pane still keeps its existing correction-specific keyboard behaviour:

```text
↑ / ↓ = correction throttle step
hold ← / → = correction steering ramp
Space = centre correction
r = record / stop recording
s = snapshot
```

### Switching away sends safe stop/reset

When leaving `Manual pad`, the browser sends a manual STOP through `/api/control/stop`.

When entering `Manual pad`, the AI correction vector is reset to zero and saved AI settings mark manual correction as disabled. This prevents the additive correction state from remaining active while the user is doing direct manual takeover.

## Preserved behaviour / rollback safety

Checked against the latest current code state and accepted patch notes:

- `0_10_5`: helper-module split for `ai_correction.py` and `ai_safety.py` is preserved.
- `0_10_4`: additive correction equation `AI + manual * Correction %` is preserved.
- `0_10_3`: AI correction pane, drag pad, arrow-key correction, `r` recording shortcut, `s` snapshot shortcut, and fixed-throttle protection are preserved.
- `0_10_2`: green Manual Drive / AI Mode buttons, shorter labels, and removal of AI `Refresh frame` are preserved.
- `0_10_1`: one-button `Start live` workflow and Manual Drive `r` / `s` shortcuts are preserved.
- `0_10_0`: v10 stable baseline runtime, model loading, recording, overlay, and config-safety behaviours are preserved.

This patch does not change model loading, AI inference output parsing, backend correction math, backend safety-limiter math, camera startup, recording folder format, overlay geometry, motor mapping, or persistent config schema.

## Verification actually performed

Performed locally in the patched `PiSD` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All listed safe checks passed in this container.

The patch was prepared on top of a clean current state made from:

```text
PiSD_0_10_0.zip
+ PiSD_0_10_1_patch.zip
+ PiSD_0_10_2_patch.zip
+ PiSD_0_10_3_patch.zip
+ PiSD_0_10_4_patch.zip
+ PiSD_0_10_5_patch.zip
```

The non-static Flask route test was also attempted:

```bash
python3 scripts/test_ai_mode_page.py
```

It could not complete in this container because Flask is not installed here:

```text
PISD-APP-002: Flask is not installed. Run: python -m pip install -r requirements.txt
```

## Not verified here

The following still require the real Raspberry Pi/browser/hardware environment:

- live browser rendering of the new three-tab panel;
- real Chromium keyboard focus behaviour;
- real Pi camera stream;
- real snapshot and recording files;
- real motor output from the new Manual pad;
- real AI model inference.

## Suggested Pi-side check

After applying this patch on the Pi:

1. Restart PiSD and hard-refresh `/ai-mode`.
2. Confirm the panel title is `Limiter / correction / manual`.
3. Confirm the tab strip shows `Limiter`, `Correction`, and `Manual pad`.
4. Confirm `Save AI settings` appears only once and stays visible while switching panes.
5. Confirm the safety acknowledgement and `Enable motor output` boxes stay visible in all three panes.
6. Open `Manual pad`, tick both safety boxes, and test the drag pad with wheels lifted.
7. Test keyboard manual driving: ↑/↓ throttle, hold ←/→ steering, Space STOP.
8. Switch away from `Manual pad` and confirm the car stops.
9. Return to `Correction` and confirm additive correction still behaves as `AI + manual * Correction %`.
