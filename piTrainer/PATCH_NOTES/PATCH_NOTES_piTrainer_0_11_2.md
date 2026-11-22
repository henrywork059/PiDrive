# PATCH NOTES — piTrainer_0_11_2 Atomic recording metadata edits (U17)

## Request summary

Implement roadmap U17: prevent recording-metadata loss if individual/bulk label editing, hide/recover, or permanent hidden-frame deletion is interrupted while saving labels.jsonl or records.jsonl. Keep a recovery copy of pre-edit metadata and report save conflicts in the UI.

## Root cause

The existing edit_service.py and delete_service.py directly opened original metadata with path.open('w'). This truncates source files before a replacement is fully written, so a process crash or storage error could leave partial or empty JSONL. The edit-service cache also retained mutable parsed records and could show uncommitted values after a failed write.

## Baseline and anti-rollback

- Built forward on draft piTrainer **0.11.1 PR #13**, preserving its U11 grouped train/validation splits and U15 collision-proof preprocessing save folders.
- Before changes, edit/delete and all three affected Data-page files matched the live GitHub PR #13 source blob hashes byte-for-byte against the uploaded 0.11.0 baseline.
- Reviewed patch notes 0.11.1 and 0.11.0, plus 0.10.6, 0.10.5 and 0.10.4 (0.10.3 for resizing history).
- Preserves docking, numbered workflow tabs, Data default sorting, Session Source multiselect and manual resize, preview debounce, bulk-edit selection, soft-delete/recover shortcuts, model non-overwrite saves, Validate edit-return, and export and runtime settings.
- No existing session data or application config is modified by applying this source-code patch.

## Files changed

- piTrainer/piTrainer/services/data/jsonl_atomic_service.py (new)
- piTrainer/piTrainer/services/data/edit_service.py
- piTrainer/piTrainer/services/data/delete_service.py
- piTrainer/piTrainer/pages/data_page_filter_edit.py
- piTrainer/piTrainer/pages/data_page_deploy.py
- piTrainer/piTrainer/pages/data_page_visibility.py
- piTrainer/piTrainer/version.py
- piTrainer/tests/test_metadata_atomicity.py (new)
- piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_2.md (new)

## Exact behavior

1. Writes are staged in unique temporary files in the same directory as the destination JSONL, flushed/fsynced, permission-matched and **atomically replaced using os.replace**. Temporary files are removed after errors; source bytes remain untouched on a failed staging write.
2. Before the **first** replacement of each JSONL file, piTrainer stores a full, synced recovery snapshot named labels.jsonl.pitrainer-original.bak or records.jsonl.pitrainer-original.bak. A later edit never overwrites this initial recovery copy. A failed backup creation refuses the metadata edit. A completed staged backup is published without overwriting existing backups.
3. Source identity includes device/inode, mtime_ns and size; edits reject a disk file changed or replaced externally since it was loaded, including equal-size replacements. This also strengthens stale JSONL cache detection.
4. Single-frame, queued preview, and bulk label edits operate on independent deep copies of cached JSONL objects; the cache is replaced with committed contents only **after a successful write**. A failed edit does not silently pollute later reads.
5. Soft-hide, recover-last/recover-all, and permanent hidden-row removal use the same atomic per-file save path. Permanent image deletion is not started when a metadata replacement fails within that operation.
6. Unknown/malformed lines, frame identifiers, and unedited steering/throttle values are preserved exactly as before.
7. Data page UI displays an explicit save failure message (including instructions to reload the affected sessions) for edit, bulk edit, applied AI output, hide, recover and permanent deletion operations; no success state is applied on a failing call.
8. The application version advances to 0.11.2 / piTrainer_0_11_2 without changing the established version scheme.

## Verification actually performed

In the local environment, the code began with piTrainer_0_11_0.zip. All affected prepatch source files were confirmed identical to the GitHub PR #13 baseline. The new 0.11.2 changed Python files and tests were uploaded by exact Git blob-hash comparison against the local tested files.

- python -m unittest discover -s tests -p 'test_metadata_atomicity.py' -v — **18 tests passed**.
- python -m unittest discover -s tests -q — **18 tests passed** in the locally available baseline.
- python -m compileall -q piTrainer tests main.py — passed.
- Tests cover per-file atomic editing, interruptions and disk-full simulation, fsync/rename failures, one-time recovery snapshots, backup failure refusal, source permissions, same-size external replacement, writes racing during staging, cache consistency, single/batch edits, soft hide/recovery and permanent deletion.
- The prior PR #13 dataset-integrity suite was not rerun in this checkout; its modified split/preprocess code is unchanged in this stacked PR.

## Known limits and next steps

- Atomicity is **per JSONL file**, not transactional across labels.jsonl and records.jsonl. If the first commits and the second fails, users should reload and reconcile the pair. The UI explicitly warns about this.
- Signature comparison is optimistic: a third-party live recorder changing the original between the final signature check and os.replace can still race. True concurrent recording needs a common cross-process lock or transactional journal.
- The first recovery copy requires storage approximately equal to the pre-edit metadata and a filesystem that supports publishing its staged backup via a hard link. If that is unsupported, the save fails closed without modifying the original; older recovery copies are never overwritten.
- Real Windows PySide6 event-loop operation, NTFS error handling and writes to a live PiSD session **were not tested**. Test on a Windows workstation and preferably against a disposable copy of recordings before merging.
- This patch does not update CustomDrive, PiSD, PiServer, or any persistent runtime configuration.
