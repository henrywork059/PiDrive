# PiSD 0.11.4 Patch Notes

## Request summary
- Make the default **Manual speed** `0.80`.
- Make settings global across the whole PiSD app.
- Avoid duplicate or similar page-local settings.
- Ensure Camera FPS changed from AI Mode is saved to the same local global settings file used by the rest of the app.

## Baseline and anti-rollback check
- Built from the user-provided `PiSD_0_11_0.zip` baseline with accepted patches `0_11_1`, `0_11_2`, and `0_11_3` applied first.
- Reviewed the latest patch note and previous three PiSD notes before finalizing:
  - `PATCH_NOTES_PiSD_0_11_3.md`
  - `PATCH_NOTES_PiSD_0_11_2.md`
  - `PATCH_NOTES_PiSD_0_11_1.md`
  - `PATCH_NOTES_PiSD_0_11_0.md`
- Preserved the 0.11.3 top-right AI workflow confirmation placement.
- Preserved the 0.11.2 AI workflow settings popup and manual-pad-release preview fix.
- Preserved the 0.11.1 AI preview/manual separation, AI-safe recording labels, and yellow preparatory buttons.
- Preserved the 0.11.0 single safety confirmation semantics.

## Cause / root cause
- Manual speed still had the old `0.18` default in several places:
  - backend settings defaults;
  - Manual Drive page markup;
  - Manual Drive JavaScript fallback;
  - Settings page markup and UI normalisation;
  - AI Mode manual takeover slider;
  - Main Dashboard manual movement controls.
- Manual Drive still allowed an older browser-local legacy key to override the backend speed, so the backend global setting was not always the only source of truth.
- AI Mode Camera FPS used the camera-specific apply endpoint directly. That endpoint already persisted camera config, but using the global settings apply endpoint makes the workflow clearer and keeps Camera FPS tied to the single global `settings.camera.fps` source.
- `/api/ai/status` did not return `camera` or `settings`, so AI Mode could not refresh its page controls from the global settings state.

## Files changed
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/templates/ai_mode.html`
- `PiSD/pisd/web/static/js/ai_mode.js`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/scripts/test_ai_mode_page.py`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_4.md`

## Exact behavior changed

### Manual speed default is now 0.80
- New runtime settings use:

```json
"manual_drive": {
  "speed": 0.8
}
```

- Manual Drive, Settings, AI Mode manual takeover, and Main Dashboard now show `0.80` as the default manual speed when no saved value exists.
- Existing saved `manual_drive.speed` values are preserved. This avoids overwriting user-local runtime settings.

### Manual speed uses one global setting
- Manual Drive no longer reads or writes the old browser-local `pisd.manualDrive.v1` speed key.
- Manual Drive loads speed from `/api/settings` and saves speed to `/api/settings`.
- AI Mode manual takeover now loads the same `manual_drive.speed` and `manual_drive.max_speed_limit` from global settings.
- Changing AI Mode manual takeover speed saves back to `/api/settings` as `manual_drive.speed`.
- Main Dashboard manual speed now loads from global settings and saves changes back to `/api/settings`.
- The Settings page still edits the same `manual_drive.speed` field.

### Camera FPS uses one global setting
- AI Mode Camera FPS popup now loads from `/api/settings`.
- Applying Camera FPS in AI Mode now posts to `/api/settings/apply` with:

```json
{
  "camera": {
    "fps": <value>
  }
}
```

- This saves `camera.fps` to `config/runtime_settings.json` and applies it to the live camera service.
- `/api/camera/apply` still exists for compatibility and testing tools, but now fails loudly if the camera service applies settings and the global settings save fails.

### AI Mode status now carries global settings
- `/api/ai/status` now returns:
  - `camera`
  - `settings`
  - `source_of_truth: "config/runtime_settings.json"`
- AI Mode can refresh Camera FPS and Manual speed from the same backend state used by the rest of the app.

### Settings page no longer writes unsaved edits as global cache
- The Settings page no longer writes every unsaved form input into the runtime settings browser cache before the backend accepts it.
- The browser mirror is only updated after backend load/save/reset responses.
- Panel presentation can still preview immediately in the browser, but global runtime settings come from the backend settings API.

## Compatibility / migration notes
- No config file rename or schema break.
- Existing `config/runtime_settings.json` values are preserved.
- Existing saved `manual_drive.speed` values are not forced to `0.80`.
- To use the new default on a Pi that already has a saved speed, change Manual speed once in Manual Drive, AI Mode manual takeover, Main Dashboard, or Settings; it will save to the shared global setting.
- `/api/camera/apply` remains available, but `/api/settings/apply` is now the preferred path for settings-style UI updates.

## Verification actually performed
Passed locally from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
node --check pisd/web/static/js/settings_tab.js
node --check pisd/web/static/js/main_dashboard.js
python3 scripts/test_settings_persistence.py
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Results:
- Python compile check passed.
- JavaScript syntax checks passed.
- Settings persistence test passed.
- AI Mode static/source contract test passed.
- Manual Drive static/source contract test passed.
- Standard validation passed with API/camera/motor/GUI skipped.
- `PiSD.py --status-only` returned OK status in this container.

## Known limits / next steps
- Hardware camera/motor behavior was not tested in this container.
- Full Flask route tests were not run here because Flask is not installed in this container.
- On the Pi, confirm this workflow:
  1. open Settings and confirm Manual speed shows `0.80` when no saved speed exists;
  2. change Manual speed in Manual Drive and reload AI Mode to confirm the same value appears;
  3. change Manual speed in AI Mode manual takeover and reload Manual Drive to confirm it follows;
  4. change Camera FPS in AI Mode Settings and confirm Settings page camera FPS shows the same saved value;
  5. restart PiSD and confirm both values survive restart through `config/runtime_settings.json`.
