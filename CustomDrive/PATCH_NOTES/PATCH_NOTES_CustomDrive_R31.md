# CustomDrive GUI R31 — Confirmed settings and explicit retry

## Request and cause
The GUI previously called two endpoints (motor and runtime) and reported “Drive settings saved” without checking `saved:false` or whether runtime throttle/mix/bias were persisted **after** the second request. AI overlay auto-save similarly trusted HTTP 200 without querying the saved manual configuration. Settings could appear applied despite partial failure.

## Baseline and anti-rollback
Built on live R30 **CustomDrive PR #38** (`update/customdrive-r30-preview-freshness`), itself on U29 PR #36 and U28 PR #34. Reviewed latest R30, U29, 0_5_20, 0_5_19 notes and Mission 1 U22/U24 history. Verified GUI launcher `CustomDrive/run_custom_drive_gui.py`, current GUI API status/motor/manual-config routes and HTML/CSS. Preserves preview-age/disconnect/backoff, U29 deterministic replay, Mission 1 failure latch and rearm, pickup/drop-off guides, model/AI deployment, saved manual/arm settings, manual motor pad, hardware ownership and watchdog.

## Files
- `CustomDrive/custom_drive/gui_web/static/app.js`: independent Drive/AI Unsaved, Applying, Applied, Failed. Reject `saved:false`, GET live config + disk-backed readback, retry current form, protect in-flight edits, debounce AI settings as before.
- `CustomDrive/custom_drive/gui_control_app.py`: additive `POST /api/gui/runtime/save` calls existing `ControlService.save_runtime_config()` after the existing motor then control flow, reads persisted config and compares motor/runtime numeric keys, returns `ok:false` on any failure; does **not** issue motor commands. GUI version 0_3_12, not Mission 1 version.
- `CustomDrive/custom_drive/gui_web/templates/index.html` and `static/styles.css`: compact indicators, descriptions and manual retry controls.
- `CustomDrive/custom_drive/gui_web/static/settings_feedback.js` and `CustomDrive/tests/test_settings_feedback.cjs` (new): pure deterministic helper/test.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R31.md`: this note.

## Runtime and persistence behavior
Drive preserves accepted motor-apply-before-control order (motor stop behavior unchanged); then saves the now-updated runtime settings without a motor command and requires saved disk readback plus live GET confirmation. AI auto-save validates `/api/ai/config` and GET `/api/manual-config`. A partial failure shows Failed and exposes retry. New edits during applying remain Unsaved and do not get overwritten by late replies. No automatic motor retry. Stage-only model and input-size changes still require Deploy, not described as deployed.

## Verification
15/15 deterministic state/readback regression tests executed through V8 CommonJS-compatible harness, final JavaScript syntax parsed. GitHub immediate-predecessor change comparison reported in PR. Full Flask, GPIO, camera, actual robot and Windows GUI testing not run.

## Limits
Persistence verification is from the existing ConfigStore disk-backed loader, but not a reboot cycle or physical actuation test. Multi-step Save is not atomic: an earlier endpoint may succeed before a later endpoint fails; retry is explicit. Existing AI model deployment semantics and safety controls are untouched. R31 does not retrofit Mission 1 web settings or headless UI.
