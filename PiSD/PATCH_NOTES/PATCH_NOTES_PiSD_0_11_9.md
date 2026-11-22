# PATCH NOTES — PiSD_0_11_9: recording manifest integrity and recovery (U20)

## Request summary

Implement roadmap U20: detect partial PiSD recording sessions; provide an explicit, non-destructive offline recovery mechanism for missing JSONL records/labels and stale manifest counts; retain existing frame IDs, two-JSONL contracts, daily snapshots and trainer compatibility.

## Root cause / observed risk

PiSD persists each frame in separate steps: JPEG, overlay sidecar/history, full `records.jsonl` row, trainer-friendly `labels.jsonl` row, and manifest update. Power loss or an interrupted write between steps can leave a frame with only one metadata row, an unindexed JPEG, a malformed JSONL tail, or a `running: true`/stale `frame_count` manifest. This is a fault-model risk; no actual lost user recording was observed.

Another issue: `RecordingService.stop()` previously finalized the manifest after a three-second thread join even if the thread remained alive. The daily snapshot index previously counted only JSONL lines, so an orphan JPEG could cause a reused frame ordinal.

## Baseline / anti-rollback

- Built forward from **live GitHub draft PiSD PR #12 (`0.11.8`)**, not older copies from uploaded `PiSD_0_11_0.zip` or `PiDrive-main.zip`.
- Reviewed current 0.11.8 patch note plus previous 0.11.7, 0.11.6 and 0.11.5 notes; also checked 0.11.4 settings source-of-truth behavior.
- Preserves the accepted 0.11.7 Snapshot/live-preview fix, Manual pad → AI assist → Correction → Limiter ordering, 0.11.8 stale-camera AI latch, 0.11.6 capture/preview/inference rate separation, 0.11.5 camera restart, 0.11.4 global settings, AI assist, overlay settings history, and recording label schema.
- No runtime config, model or existing recording file is changed merely by applying this code update.

## Files changed

1. `PiSD/pisd/services/recording_recovery.py` (new) — inspect and optional repair.
2. `PiSD/scripts/recover_recordings.py` (new) — read-only CLI by default; explicit offline confirmation required for repairs.
3. `PiSD/scripts/test_recording_recovery.py` (new) — 18 fault-model and piTrainer-loader tests.
4. `PiSD/pisd/services/recording_service.py` — refuse premature manifest finalization when capture thread remains alive; keep daily screenshot frame index above already-present orphan JPEG numbers.
5. `PiSD/pisd/__init__.py` — version 0.11.9.
6. `PiSD/README.md` — operator instructions and migration limits; correct current patch version.
7. `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_9.md` (new).

## Exact behavior changed

- `inspect_session(session_dir)` scans the two JSONL files, manifest and JPEG directory; reports valid pairs, mismatched record/label identities by stable `frames/<filename>` key, invalid/truncated JSONL lines, duplicate IDs, missing images, orphan JPEGs, stale frame count, and whether manifest still claims to run. It makes no changes.
- An explicit `recover_session(..., confirm_offline=True)` can restore a missing label **only when a matching JPEG and a finite bounded steering/throttle command exist** in the original trace record. The record's existing training-label dictionary and visual overlay metadata are preserved.
- If the label exists without its full trace row, a **limited** trace record may be reconstructed from its valid controls and frame identity. The replacement carries a deterministic `recovered_<id>` and a `recovery.limited_metadata` flag; original camera/motor diagnostics are not fabricated.
- If neither side has metadata for an orphan JPEG, the image is preserved and reported; no fabricated steering/throttle label is added. Malformed/duplicate rows and missing image reports are never silently removed or pruned.
- Repairs append only missing counterpart rows to JSONL via same-directory temporary files and atomic replacement. Each repaired session gets a unique `.recovery_backups/<timestamp>_<id>/` directory containing untouched original metadata and an audit report before modifications.
- Manifest `frame_count` is reconciled to the complete record/label pair count; stale `running: true` is cleared only after the operator confirms offline. The historical end timestamp is left unchanged, and a `recording_recovery` audit summary is added while preserving existing manifest schema/fields.
- A second repair is idempotent: no duplicate reconstructed rows or unnecessary new backup. If the original manifest is missing/corrupt, the repair refuses to fabricate or overwrite it; inspection still reports the problem.
- The CLI rejects paths outside its recordings root and requires `--repair --confirm-offline` for writes. Default inspection never mutates the filesystem.
- The live recording loop, per-frame JSONL order, overlay sidecar writer, AI motor control, camera settings, and per-frame manifest write cadence remain unchanged. `stop()` now returns an error without finalizing an active capture thread that did not stop within its join timeout.

## Verification actually performed

Against the uploaded PiDrive monorepo baseline, with the new files and targeted recording-service changes:
- `cd PiSD && python scripts/test_recording_recovery.py -q`: **18 passed** including actual piTrainer `load_records_dataframe` support.
- `python scripts/test_recording_service.py`: **11/11 service checks passed**, covering single captures, continuous recording, both JSONLs, overlay sidecars, collection listing/download/delete, and metadata schema.
- `python -m compileall -q pisd scripts PiSD.py`: passed.
- Tests include every interruption phase, healthy/no-op scans, orphan JPEG, malformed tail, duplicate frames, missing JPEG, invalid controls, invalid/missing manifest, recovery backups, interrupted replace, stale running manifest, idempotent repairs, secure CLI path restrictions, daily screenshot ordinal collision, and hung recording-thread stop protection.
- GitHub blobs for the **three new standalone Python files** matched their locally tested file SHA values exactly. The existing service was patched via exact single-occurrence anchors on the live PR #12 source, preserving its newer AI-specific recording behavior.

## Known limits / follow-up

- Repair must be run on an **offline** session. `--confirm-offline` is the operator's assertion, not a cross-process lock. Concurrent unpatched recorders could still race with optimistic byte checks.
- Per-file replacement is atomic; the two JSONL files and manifest are not one multi-file transaction. If an interrupted repair commits one file then fails, preserve backups and rerun; the process is idempotent.
- A reconstructed full record is intentionally incomplete telemetry. Never interpret those records as original motor/camera measurements.
- An orphan image with no trustworthy label cannot be used for supervised training without manual annotation.
- Large sessions require a full scan; the CLI is intentionally explicit and runs offline rather than scanning all sessions in the live preview loop.
- Real Pi 4 camera/SD-card fault injection, live Flask UI, Windows piTrainer workflow and power-cut durability were **not** tested. Test on disposable recordings before applying repair to valuable data.
- This patch builds on PR #12; review/merge that PR before this one. No unrelated component touched.
