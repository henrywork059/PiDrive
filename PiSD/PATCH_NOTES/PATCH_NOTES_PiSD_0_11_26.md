# PiSD 0.11.26 — Batch 2 / F7 preserve damaged configuration

## Request and root cause
SettingsManager previously loaded defaults after malformed JSON and could overwrite the only recoverable original on a later save. A failed write also changed in-memory settings before persistence succeeded.

## Changes
- core/config_recovery.py: deterministic byte-for-byte sibling recovery backup with exclusive creation, private permissions, verification and fsync; no write when preservation fails; atomic temporary-file replacement with detected external-change check; local path in local log, basename-only warning in API.
- core/settings_manager.py: use the existing normalizer for valid documents, preserve invalid object/group data, keep last effective settings after failed load/save/reset, commit memory only after disk replacement. No schema or default reset.
- app.py: expose recovery diagnostics in status/settings and distinguish motor/model persistence failures from runtime actions.
- settings_tab.html/js: visible recovery warning in current settings panel; keep R31 feedback.
- scripts/test_config_recovery_f7.py: malformed and external damage, backup/replace failure, valid unknown nested key, restart, warning and STOP integration cases. Workflow includes tests.
- README and version 0.11.25 -> 0.11.26.

## Baseline and verification
Parent 413b938 (F3 exact CI 45357578563 all four jobs green); reviewed latest 0.11.25, 0.11.24, 0.11.23 and 0.11.22 notes, actual settings manager, API, UI and launcher. No persistent config file included, no motor/camera logic or old UI replacement. New CI required; no hardware verification. Recovery copies are for manual inspection, not automatic rollback. Single-process lock and external-change detection are not a cross-process locking guarantee. PiServer F7 and UX74 are separate outstanding changes.
