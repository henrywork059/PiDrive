# PiServer 0_4_30 — Batch 2 / F7 configuration recovery

## Request and cause
ConfigStore.load_raw silently returned an empty object on malformed JSON, allowing later saves to overwrite the only recoverable original. Reload could apply fallback defaults to a running controller.

## Changes
- core/config_recovery.py: verified byte-for-byte sibling recovery copy, exclusive creation and private permissions, fsync and atomic replacement; block writes if original cannot be read/preserved or changes during save.
- core/config_store.py: retain last valid raw state on failed read; preserve unknown valid keys across runtime saves; do not change existing default or scalar normalization policy; lock serialized store operations.
- services/control_service.py: reject reload after parse/read failure without applying fallback configuration.
- app.py: status and save/reload diagnostics, truthful errors, version 0_4_29 -> 0_4_30.
- web/templates/index.html and web/static/app.js: independent visible recovery warning in Status dock, preserving safety/status banner and existing UI.
- tests/test_config_store.py and test_config_recovery_f7.py: corruption, recovery, restart, failure, unknown-key retention, real API fixtures and STOP; include both files in CI.
- README documents recovery.

## Verification and anti-rollback
Reviewed actual server.py, ConfigStore, control service, current APIs and UI plus 0_4_29/28/27/26 notes. Parent f11abb02 is layered on the fully green Batch 1 candidate 413b938. No runtime JSON, camera/motor algorithms, access policy, emergency STOP or retired component changes. New exact-commit CI required. No hardware or real-browser acceptance claimed. Recovery files require manual review; no cross-process lock guarantee. UX74 remains separate.
