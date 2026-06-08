# PiSD 0.10.3 Patch Notes

## Request summary

This patch builds forward from `PiSD_0_10_0` plus the accepted `0_10_1` and `0_10_2` patches.

Requested AI Mode changes:

- Make the AI Mode `Snapshot` action green.
- Add AI Mode keyboard shortcuts:
  - `s` saves a snapshot.
  - `r` toggles recording.
- Extend the AI Mode `Output limiter` panel into a two-pane `Limiter / correction` panel.
- Add a second correction pane where the user can manually correct AI output.
- Blend AI prediction with manual correction by a user-settable percentage.
- Use the same manual correction style as Manual Drive: drag pad and arrow keys.
- Preserve fixed-throttle behaviour: if fixed throttle mode is selected, final throttle remains the configured fixed throttle.

## Cause / root cause

The previous AI Mode UI had recording/snapshot controls, but `Snapshot` still inherited a neutral/secondary style in some selector paths. AI Mode also did not have the same `r` and `s` keyboard shortcuts already accepted for Manual Drive.

The previous safety panel only exposed output limiting controls. There was no guarded way to add human correction into the AI command stream before the existing safety limiter and motor-output acknowledgement checks.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/css/ai_mode.css`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_3.md`

## Behaviour changed

### AI Mode controls

- AI Mode `Snapshot` and `Record` controls now use green action styling.
- `s` saves an AI Mode snapshot when focus is not inside an input, textarea, select box, or editable element.
- `r` toggles AI Mode recording under the same focus guard.
- The removed `Refresh frame` action remains absent.

### Limiter / correction panel

- The old AI Mode `Output limiter` panel is now `Limiter / correction`.
- The panel has two panes:
  - `Limiter`: the existing output-mode, max throttle, max steering, smoothing, update-rate, and motor-output acknowledgement controls.
  - `Correction`: the new manual AI-correction controls.
- Switching to `Correction` enables manual correction in AI config.
- Switching back to `Limiter` disables manual correction and sends a centred correction vector.

### Manual AI correction

- The correction pane adds a Manual Drive-style drag pad.
- Arrow-key behaviour matches the current Manual Drive method:
  - Up/down adjust manual correction throttle by `0.05` per press.
  - Holding left/right ramps steering toward full scale in about `0.8 s`.
  - Space centres the correction vector.
- The new API endpoint `/api/ai/manual-correction` accepts guarded manual correction vectors.
- Manual correction is bounded to `[-1.0, 1.0]` for steering and throttle.
- Manual correction includes a short timeout so stale correction input is dropped if updates stop.

### AI/manual blending

When manual correction is enabled, AI output is blended before the existing AI safety limiter:

```text
mixed steering = ai steering * (1 - manual_mix) + manual steering * manual_mix
mixed throttle = ai throttle * (1 - manual_mix) + manual throttle * manual_mix
```

where `manual_mix` is set by the user as `Manual mix %` from `0` to `100`.

The existing safety layer still runs after blending. In `AI steering + fixed throttle` mode, the final throttle still comes from the configured fixed throttle after blending, so manual throttle correction does not override the fixed-throttle workflow.

### Status reporting

AI Mode status now exposes:

- `last_raw_prediction`: model-only prediction.
- `last_mixed_command`: AI/manual blended command before safety output.
- `manual_correction`: current manual correction state, mix percentage, age, active/expired status, and source.
- `safety_layer.manual_correction_enabled`.
- `safety_layer.manual_mix_percent`.
- `safety_layer.manual_correction_timeout_s`.

## Rollback / anti-regression notes

This patch was built forward from the accepted v10 state and preserves:

- `0_10_1` one-button `Start live` workflow.
- `0_10_1` Manual Drive `r` record and `s` snapshot shortcuts.
- `0_10_2` green Manual Drive / AI Mode cards and shortened button labels.
- `0_10_2` removal of the AI Mode `Refresh frame` button.
- AI Mode model upload/delete/load/runtime diagnostics.
- AI Mode shared recording service usage.
- Existing safety acknowledgement and motor-output enable gates.
- Existing fixed-throttle output mode.
- Existing Manual Drive keyboard and drag-pad paths.
- Existing overlay rendering and recording sidecar metadata.

## Verification performed

Performed locally in the packaging container from the patched `PiSD` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
```

Also performed a direct `AIDriveService` check that confirmed:

- 50% manual mix blends opposite AI/manual values to zero.
- 100% manual mix uses the manual correction value before safety.
- `AI steering + fixed throttle` mode still outputs the fixed throttle after mixing.

The patch was also applied over a clean `PiSD_0_10_0` extraction with `PiSD_0_10_1_patch.zip` and `PiSD_0_10_2_patch.zip` before re-running the same safe static checks.

## Not verified here

The following require the real Raspberry Pi/browser/hardware environment:

- Real Pi camera live preview.
- Browser keyboard shortcut behaviour in Chromium on the Pi.
- Real snapshot files from the camera stream.
- Real recording session files while AI Mode is running.
- Real motor output.
- Real AI model inference through an installed TFLite/TensorFlow backend.

The full Flask route/API test was not run successfully in this container because Flask is not installed in the container environment. On the Pi or development venv with dependencies installed, run:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_ai_mode_page.py
```

That non-static test includes the `/api/ai/manual-correction` route contract.

## Suggested Pi-side check

After applying this patch on the Pi:

1. Hard refresh `/ai-mode` in the browser.
2. Confirm `Snapshot` and `Record` are green.
3. Press `s` and confirm a snapshot is saved.
4. Press `r` and confirm recording toggles.
5. Open `Limiter / correction` → `Correction`.
6. Drag the correction pad and test arrow keys while watching the mixed command readout.
7. Test `AI steering + fixed throttle` and confirm throttle remains the fixed value during correction.
