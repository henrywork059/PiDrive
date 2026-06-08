# PiSD 0.10.8 Patch Notes

## Request summary

Fix AI Mode `Max throttle` settings persistence. The user reported that Max throttle always returns to the default value instead of staying saved.

This patch builds forward from the uploaded `PiSD_0_10_0.zip` v10 baseline plus accepted patches `0_10_1` through `0_10_7`.

## Cause / root cause

The backend settings path already supported saving `ai_mode.max_throttle` into `config/runtime_settings.json` through `POST /api/ai/config` and `SettingsManager.save()`.

The practical reset risk was in the AI Mode browser page:

- `/api/ai/status` refreshes frequently while AI Mode is running.
- `renderAI()` called `renderConfig()` on every status payload.
- `renderConfig()` repainted the limiter form directly from the last saved AI settings.
- While the user was editing `Max throttle`, a status refresh could repaint the slider back to the old saved/default value before the user pressed Save.
- If Save was pressed after that repaint, the page could send the old/default value again.

This made the UI feel as if Max throttle could not be saved.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/AI_MODE_CODE_MAP.md`
- `PiSD/docs/STABLE_BASELINE.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_10_8.md`

## Behaviour changed

### Max throttle no longer gets overwritten during status refresh

AI Mode limiter/config fields now have dirty-field protection in `ai_mode.js`.

When the user edits `Max throttle`, the field is marked dirty. While it is dirty or focused, normal `/api/ai/status` refreshes no longer repaint that field with the old saved/default value.

### Max throttle auto-saves after editing

`Max throttle` now schedules an automatic config save while being edited and saves immediately on change/release.

The same persistence guard is applied to the other AI limiter controls for consistency:

- Output mode
- Max throttle
- Max steering
- Fixed throttle
- Update Hz
- Steering smoothing
- Throttle smoothing
- Correction %

The existing single `Save AI settings` button remains available and unchanged.

### Confirmed-save repaint only

After `POST /api/ai/config` succeeds, the page clears the dirty state and force-renders the form from the confirmed saved settings returned by the backend.

If the user edits again while a save is in flight, the next save is queued instead of silently losing the newer edit.

## Preserved behaviour / rollback safety

Checked against the latest current code state and previous accepted patch notes:

- `0_10_7`: AI Mode `Records & snaps` panel and global Space STOP helper are preserved.
- `0_10_6`: three-way `Limiter / correction / manual` panel and full Manual pad takeover are preserved.
- `0_10_5`: smaller AI helper modules for correction and safety math are preserved.
- `0_10_4`: additive equation `AI + manual * Correction %` is preserved.
- `0_10_3`: AI Mode `r` recording shortcut and `s` snapshot shortcut are preserved.
- `0_10_2`: green AI Mode / Manual Drive entry buttons and shortened AI labels are preserved.
- `0_10_1`: one-button `Start live` workflow is preserved.
- `0_10_0`: v10 model loading, recording, overlay, and runtime/config safety behaviours are preserved.

This patch does not change AI correction math, AI safety limiter math, fixed-throttle behaviour, motor mapping, model loading, camera startup, recording folder format, overlay geometry, Space STOP routes, or Manual pad command routing.

## Verification actually performed

Performed locally in the patched `PiSD` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/ai_mode.js
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --status-only
```

Results:

- Python compile checks passed.
- AI Mode JavaScript syntax check passed.
- AI Mode static/source/helper checks passed.
- Added settings persistence check passed: `ai_mode.max_throttle` saves and reloads through `runtime_settings.json`.
- Standard validation passed with GUI/static checks and with GUI skipped.
- Status-only command returned `PISD-OK-000` in simulation mode.

The patch was prepared on top of a clean current state made from:

```text
PiSD_0_10_0.zip
+ PiSD_0_10_1_patch.zip
+ PiSD_0_10_2_patch.zip
+ PiSD_0_10_3_patch.zip
+ PiSD_0_10_4_patch.zip
+ PiSD_0_10_5_patch.zip
+ PiSD_0_10_6_patch.zip
+ PiSD_0_10_7_patch.zip
```

## Not verified here

The following still require the real Raspberry Pi/browser/hardware environment:

- real browser interaction with the Max throttle slider during live AI status refresh;
- real persistence through PiSD restart on the Pi;
- real Pi camera stream;
- real motor output;
- real AI inference;
- real recording/snapshot files.

## Suggested Pi-side check

After applying this patch on the Pi:

1. Restart PiSD and hard-refresh `/ai-mode`.
2. Change `Max throttle` from `0.22` to a clear different value, for example `0.35`.
3. Keep AI status refresh active, or start AI preview, and confirm the slider does not jump back to `0.22`.
4. Hard-refresh the page and confirm `Max throttle` still shows the new value.
5. Restart PiSD and confirm it still shows the new value from `config/runtime_settings.json`.
6. Confirm Start live, Snapshot, Record, Records & snaps, Correction, Manual pad, and Space STOP still work.
