# PATCH NOTES — PiSD_0_11_11: recording storage safety (U26)

## Request summary
Implement U26: warn on low SD-card free space, refuse new recording/capture writes at critically low capacity, stop *recording only* when a write fails, expose storage/session-size/write diagnostics, and require explicit deletion confirmation. Preserve existing PiSD camera, AI and motor behavior.

## Root cause / risk
Before this patch the PiSD recording service wrote JPEGs, records.jsonl, labels.jsonl and manifests without checking free space. The recording worker caught write failures and slept/retried, potentially filling the card with repeated partial writes. A full disk could leave mismatched metadata (covered by the separate U20 offline recovery tool). There was no storage utilization status.

## Anti-rollback baseline
- Built on **live GitHub PiSD 0.11.10 draft PR #22**, which is stacked on PR #20 and #12.
- Reviewed current notes **0.11.10, 0.11.9, 0.11.8, 0.11.7** and current paths/entry point.
- Preserves U23 latency telemetry, U20 recording reconciliation and snapshot ordinal safety, U21 stale-camera AI motor latch, independent FPS settings, overlay configuration/history, AI correction tabs, existing frame naming and metadata schema.
- No runtime.json, other config values, motor algorithm or legacy PiCar files changed.

## Files changed
- `PiSD/pisd/core/recording_storage.py` (new)
- `PiSD/pisd/services/recording_service.py`
- `PiSD/pisd/app.py` (delete confirmation only)
- `PiSD/pisd/web/static/js/recording_download_panel.js` (explicit UI confirmation flag)
- `PiSD/scripts/test_recording_storage.py` (new)
- `PiSD/scripts/test_recording_storage_integration.py` (new)
- `PiSD/pisd/__init__.py` (0.11.11)
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_11.md` (new)

## Exact behavior
1. Free-space guard samples `shutil.disk_usage` on the recording filesystem (nearest existing parent). Defaults: warning below **512 MiB** and critical reserve below **256 MiB**. Environment overrides `PISD_RECORDING_WARN_FREE_MB` and `PISD_RECORDING_MIN_FREE_MB` are bounded and optional. Reserved size includes estimated incoming JPEG and 128 KiB metadata; absent/failed disk telemetry refuses new writes safely. No changes to persistent runtime settings.
2. Before creating a recording session or obtaining a single capture, reject critically low/unavailable storage without creating new session data. Before each JPEG/metadata write, check estimated space again.
3. On any recording-loop write/finalisation exception, capture the error, stop the recording worker rather than retrying indefinitely, and attempt to close its manifest. If finalisation also fails, preserve session metadata for the **0.11.9 offline recovery tool** and expose an error. Do not automatically delete files or invent missing labels.
4. A failed active-session capture requests the recording worker to stop. A successful single capture updates the last-session path for size reporting. Both camera and motor adapter objects are left untouched by recording-storage failures.
5. Existing `/api/recording/status` (also represented in the global status) now returns nested `recording.storage` including `state`, `free_bytes`, `total_bytes`, thresholds, up to five write errors, last/active session `session_size_bytes` and `cleanup_policy`. Size scans are cached for 2 seconds.
6. The already-confirmed selected-folder deletion UI now passes `confirm: true`. The deletion API rejects omitted/false confirmation before calling the existing safe `delete_collection` guard. An active session or incorrect root/kind still cannot be deleted. No automatic retention pruning.
7. Version advances to `PiSD_0_11_11`, and README documents capacity thresholds, recovery, manual cleanup and operational limits.

## Verification actually performed
- Locally replayed the U26 storage guard and recording hooks on the available uploaded PiDrive/PiSD baseline, checking replacement anchors against the live PR #22 source. `PYTHONPATH=. python -m unittest discover -s scripts -p 'test_recording_storage*.py' -q`: **7 passed**.
- Existing `python scripts/test_recording_service.py`: **11 checks passed** (two JSONLs, overlay files, captures, recording, library ZIP and deletion safeguards).
- `python -m compileall -q pisd scripts`: passed in the local checkout.
- Full modified recording service was edited directly from the **live GitHub PR #22 blob**, not substituted by an older file.
- Both changed browser scripts passed V8 syntax parsing.
- All new helper/test files' Git blob hashes matched the locally executed source.

## Known limits
- Full **stacked 0.11.10+0.11.11 runtime** and Raspberry Pi SD-card power-cut/fault-injection were not exercised. The local behavior tests used the uploaded baseline with the same U26 hooks; rerun on the final stacked PR checkout.
- A disk failure during a multi-file write can still leave an orphan JPEG or unmatched JSONL, since writes are not a transaction. Use the offline U20 recovery tool after stopping the writer.
- The guard only protects the PiSD recording writer, not model uploads or unrelated filesystem users; it cannot guarantee the card will not fill. Thresholds need real Pi SD-card validation. Warning state is exposed via status rather than a new intrusive UI banner.
- This is software protection. Recording failures deliberately do **not** stop motors or substitute for emergency stop/watchdog hardware.
- Explicit delete confirmation remains a per-selected-folder operation; users must back up important recordings. Review/merge PR #22 before this stacked PR.
