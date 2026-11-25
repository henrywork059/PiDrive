# PiSD 0.11.36 — Batch 4 regression repair

## Cause
0.11.35 (eae6793) failed Linux 45630356406 PiSD regression, despite all 16 Chromium viewport cases passing. Two R46 source checks expected original actionable wording and explicit selected-kind variable; both standalone AI validation scripts still required /api/recording/items in recording_download_panel.js after extraction. Other three Linux jobs and Windows 45630356385 passed. Last fully green candidate 95537b4.

## Changes
- manual_drive.js: retain original actionable R46 message plus actual read error; explicit selected-kind guard restored.
- recording_reader.js: reject late body completion after abort deadline even if transport returns data.
- scripts/test_ui_copy_r46.cjs: retain existing assertions and add three deterministic real-reader tests for superseded success/failure, body deadline, rejected/malformed response and retry; use fake network and clock.
- scripts/test_ai_mode_page.py and run_standard_validation.py: verify endpoint in actual shared reader and require integration and script inclusion; retain existing delete/download/safety checks.
- pisd/__init__.py and docs/ui_regression_gate.md: version and evidence.

## Verification and anti-rollback
Reviewed current source, actual PiSD.py, exact failing CI logs, latest notes 0.11.35/34/33/32, canonical roadmap. JS syntax parsed. No tests removed or skipped, no reversal of 0.11.35 folder recovery, no backend/config/motor/STOP or other runtime component changes. Exact new CI pending; no physical/owner visual acceptance, no additional proposal closure.
