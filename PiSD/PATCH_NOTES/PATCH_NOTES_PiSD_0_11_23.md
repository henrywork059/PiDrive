# PiSD 0.11.23 — Batch 1/F4 validation and truthful STOP outcome

## Cause and request
PR #87 run 45354955594 passed the selected regression and new AI math checks, but full standard validation returned 59 passed / 4 failed. Three checks referred to an older AI heading, older settings title and a JavaScript helper incorrectly listed as an HTTP endpoint. STOP exposed a real bug: a successful STOP attached the last historical motor error and did not distinguish current adapter failure or failed AI stop.

## Changes
- scripts/run_standard_validation.py: match accepted heading, assist controls and settings Apply/STOP markers; require actual HTTP routes in manifest; assert present zero logical and hardware command outputs plus ok/code.
- pisd/services/motor_service.py: return boolean current stop result; preserve diagnostic history.
- pisd/services/ai_drive_service.py: refuse rearm and report stop/override failure on explicit adapter false (legacy test doubles returning None remain compatible).
- pisd/app.py: disable AI output on preview-preserving STOP; report current motor or AI stop failure rather than stale error.
- scripts/test_stop_outcome_f4.py, scripts/test_safety_rearm.py: regression cases for prior error, adapter failure, AI stop failure, preview-only ownership and rearm.
- pisd/__init__.py: 0.11.22 -> 0.11.23; workflow includes new tests.

## Anti-rollback and verification
Direct parent 216d352375250961f53d299a3a845537b62452a8 (PR #87); reviewed 0.11.22, R48, R47, R46, F4 follow-up note and PiSD.py, live routes, motor/AI services and UI templates. No config/defaults change, no older archive, no layout or motor mixing changes. Prior CI failures confirmed in logs; new exact-branch CI required. No physical test performed. Commanded zero is not physical motor feedback. F2/F3 remain pending; do not promote without hardware safety verification.
