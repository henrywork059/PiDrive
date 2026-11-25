# PiSD 0.11.34 — Batch 4 Settings read timeout and safe retry (UX75/R35)

## Request and root cause
Continue Batch 4 from fully verified e901060 (Linux 45591973241, Windows 45591973183). Settings GET lacked a deadline, manual Load and Retry could escape a rejected promise, and pending reads were not serialized with Save/Apply. Failure logs with no code could appear successful.

## Changes
- pisd/web/static/js/settings_tab.js: bounded 3500ms GET including JSON body, explicit Loading state, caught failure and retry, prevent concurrent settings operations, retain draft edits via revision guard, report missing failure code as error. No client timeout added to POSTs or STOP.
- pisd/web/static/js/settings_feedback.js: optional read-specific begin feedback, existing mutation defaults and token/revision semantics preserved.
- pisd/web/static/css/settings_tab.css and templates/settings_tab.html: reuse existing pending colour and announce detail with polite live region.
- scripts/test_settings_feedback.cjs: three deterministic load-lock/retry/edit cases.
- tools/check_browser_ui.py: native four-width stalled GET/retry/recovery and held read plus draft edit; existing rejected Save/STOP regression retained, all mutations intercepted.
- pisd/__init__.py and docs/ui_regression_gate.md: patch version and evidence.

## Anti-rollback and verification
Reviewed actual PiSD.py, current template/JS, current regression workflow, canonical roadmap, latest four patch notes 0.11.33/32/31/30. No settings schema, local keys, hardware commands, motor lease, model provenance, recording, layout or inactive component changes. Previous exact candidate 5/5 green; new browser and JS tests await exact CI. Browser response timeout is not a hardware stop guarantee. Owner visual acceptance, actual training and physical Raspberry Pi testing remain separate.
