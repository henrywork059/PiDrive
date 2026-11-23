# PiSD 0.11.14 — R31 settings confirmation and retry

## Request and root cause
PiSD Settings previously displayed a successful response or updated local storage even when an HTTP-success response contained `ok:false`. The shared runtime apply helper also ignored a camera service `(ok, message, config)` failure. As a result Save/Apply status could be misleading.

## Exact source and anti-rollback
Stacked directly on PiSD U29 PR #35 (`update/pisd-u29-offline-replay`), itself based on U28 PR #32. Reviewed U29, 0.11.13, 0.11.12, 0.11.11 and 0.11.10 notes. Inspected `PiSD/PiSD.py`, `pisd/app.py`, settings manager, camera/motor/AI apply methods and actual Settings HTML/JS/CSS. Preserves U29 replay, U28 safety latch/rearm, U27 model metadata, U26 storage protections, U21 stale-frame safety, global STOP, manual/AI/overlay/panel presentation controls, and persistent configuration paths.

## Files
- `PiSD/pisd/app.py` — fail the aggregate apply result if camera service reports `ok=false`, rather than claiming all services applied.
- `PiSD/pisd/__init__.py` — version marker 0.11.14, continuing the existing line.
- `PiSD/pisd/web/static/js/settings_tab.js` — distinct Unsaved/Applying/Applied/Failed; guarded POST/GET and readback equality, save-only never claimed runtime-applied; retry current form; stale in-flight response cannot overwrite newer edits.
- `PiSD/pisd/web/static/js/settings_feedback.js` (new) — pure state/readback helper.
- `PiSD/pisd/web/templates/settings_tab.html` and `PiSD/pisd/web/static/css/settings_tab.css` — compact accessible status/detail/retry.
- `PiSD/scripts/test_settings_feedback.cjs` (new) — deterministic state/readback tests.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R31.md` — this note.

## Behavior and safety
Save only confirms storage by GET readback and shows Unsaved with an explicit saved-only message because runtime application is not proven; Save and apply and Reset show Applied only after checked backend success and a matching GET. Rejected API, network or readback mismatch shows Failed and a Retry apply control. Operator edits during a pending save remain Unsaved; they are never overwritten by a stale response. Existing local presentation preview behavior is retained. No settings JSON reset, motor code, camera ownership or watchdog modifications.

## Verification
15/15 pure deterministic feedback tests executed with a CommonJS-compatible V8 adapter, plus full settings JS syntax parsing. GitHub branch comparison and Python compilation status are recorded in draft PR description. Full Flask and physical Raspberry Pi tests were not executed.

## Limits
Readback proves settings persistence reported by API, not actual camera exposure or motor movement. A partial multi-service apply error can leave some persisted groups applied; retry from current form is operator-controlled, not automatic. Existing save-before-apply behavior is unchanged. Avoid using Save only to claim runtime applied.

## Accepted-value normalization
The backend may clamp or normalize submitted values. R31 checks the backend-accepted response against independent readback, then displays effective values or an explicit normalization notice rather than treating valid clamping as a persistence failure. A rejected response or mismatched accepted-value readback still shows Failed.
