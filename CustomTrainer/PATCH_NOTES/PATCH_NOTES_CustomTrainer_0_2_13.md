# PATCH NOTES — CustomTrainer_0_2_13 (U25: immutable YOLO dataset cache)

## Request summary
Complete roadmap U25 for the active CustomTrainer training/validation workflows:
never delete dataset-cache files while readers are active; stage and validate new
cache generations before publication; pass immutable YAML into YOLO workers;
and permit only explicit, cautious cleanup of known idle generations.

## Root cause
The existing `dataset_service._build_dataset_spec()` unconditionally ran
`shutil.rmtree(root/.customtrainer_yolo_cache, ignore_errors=True)`.
A second preparation, including one launched on a different training page,
could invalidate the active Ultralytics worker's images, labels or train/val
lists. The root `dataset.yaml` was also rewritten in place and could change
before an asynchronous worker opened it. Cached image hard links meant an
in-place source image rewrite could mutate an already-running cache.

## Baseline and anti-rollback
- Based on the **live GitHub CustomTrainer 0_2_12 draft PR #18**, retaining its
  U18 whole-session and SHA-256 duplicate-aware split, strict YOLO annotation
  validator, and clearly warned missing holdout behavior.
- Examined the current source plus notes 0_2_12, 0_2_11, 0_2_10 and 0_2_9.
- Preserves 0_2_11 compact Marking panel, 0_2_10 Quick Deploy selected/current
  labeling, 0_2_9 Export Validate tab, keyboard shortcuts, saved splitters,
  class-name persistence, existing source labels, and all runtime config files.
- Existing cache generations/legacy caches are not automatically deleted or
  converted; no folder flattening and no changes outside CustomTrainer.

## Files changed
- `CustomTrainer/custom_trainer/services/cache_lifecycle.py` (new)
- `CustomTrainer/custom_trainer/services/dataset_service.py`
- `CustomTrainer/custom_trainer/services/ultralytics_cli.py`
- `CustomTrainer/custom_trainer/ui/pages/train_page.py`
- `CustomTrainer/custom_trainer/ui/pages/validate_page.py`
- `CustomTrainer/custom_trainer/ui/pages/export_validate_page.py`
- `CustomTrainer/custom_trainer/ui/main_window.py` (0_2_13 title)
- `CustomTrainer/manage_dataset_cache.py` (new, explicit inspect/prune CLI)
- `CustomTrainer/tests/test_cache_lifecycle.py` (new)
- `CustomTrainer/README.md`
- `CustomTrainer/PATCH_NOTES/PATCH_NOTES_CustomTrainer_0_2_13.md` (new)

## Exact behavior changed
1. Each preparation allocates a unique `.customtrainer_yolo_cache/.building/gen_*`
   directory and targets an immutable `.../generations/gen_*` directory. No
   more `shutil.rmtree(cache_root)` of an active generation.
2. Images are copied into staging rather than hard-linked to mutable sources.
   Source YOLO labels are read as before; U18's strict validation produces
   cached labels without rewriting originals.
3. Before publication, compare train/val counts and unique membership with
   actual staged images, verify no overlap, check label files equal the accepted
   labeled-image count, and validate YAML class names/count. Write generation
   local `dataset.yaml` and `cache_manifest.json` with checksums of lists.
   Rename only the complete staged directory into `generations/`; delete a
   failed private staging directory, never an earlier published generation.
4. Atomically replace the user-visible root `dataset.yaml` *after* a
   generation is complete. Legacy `find_dataset_yaml` and
   `ensure_dataset_yaml_with_summary` return signatures are unchanged.
   `DatasetSummary.cache_yaml_path` exposes the immutable per-run YAML.
5. Training, Validation, and Export Validate each pass the generation-local
   YAML path (not the mutable root pointer) into their existing
   `ultralytics_cli` subprocess. Readiness/holdout tests and UI form fields
   remain unchanged; failed cache preparation shows a clear error, and Run Log
   records which immutable YAML is actually used.
6. The child CLI holds a generation-specific OS file lease throughout
   training/validation or INT8 export when given a generated dataset.
   Linux supports shared readers; Windows uses a nonblocking exclusive
   file-region lock. Unknown external/custom YAML is left untouched.
7. No automatic pruning. `manage_dataset_cache.py` lists known generations
   and offers explicit `--prune --confirm-idle`. It retains at least two
   newest generations, currently referenced root YAML, all generations newer
   than 24h, and lease-held generations. Only valid manifest-marked
   generations are candidates. A deletion tombstone stops new readers from
   starting while cleanup runs. All unknown/legacy cache directories remain.
8. Update title to CustomTrainer `0_2_13`; documentation explains disk-space
   impact, immutable YAML paths, review and manual cleanup policy.

## Verification actually performed
- Local validation started from the uploaded `PiDrive-main.zip`
  CustomTrainer source; source hashes matched the pre-0_2_12 GitHub main.
  Replayed U25-only changes on that baseline and executed
  `PYTHONPATH=. python -m unittest discover -s tests -p test_cache_lifecycle.py -v`
  — **12/12 tests passed**.
- `python -m compileall -q custom_trainer tests manage_dataset_cache.py
  run_custom_trainer.py` passed; CLI `--help` launched successfully.
- Tests cover immutable train/val references, source image isolation, manifest
  and class/label counts, disk-full stage failure, bad list/manifest rejection,
  atomic YAML replacement errors, concurrent readers during rebuild,
  POSIX subprocess file locks and refusal to prune active/current/new snapshots,
  and preservation of the legacy cache layout.
- Live 0_2_12 GitHub source was then patched at unique exact anchors, preserving
  the U18 split and validation code. New helper/test/CLI Git blobs were matched
  against locally executed source files.
- **Not performed:** a full end-to-end 0_2_12+0_2_13 Ultralytics training run,
  PySide6 workstation UI testing, or Windows NTFS locking/fault injection.
  Run both U18 and U25 tests on the fully stacked PR checkout before merge.

## Known limits / next steps
- Generations now copy images and retain prior versions; this consumes more
  disk space. The cleanup tool requires operator confirmation and never runs
  implicitly. Users should monitor storage before building large datasets.
- External YOLO jobs using legacy/root YAML may not hold the generated cache
  reader lock. A 24-hour minimum age and explicit `--confirm-idle` guard
  remain necessary; manual deletion outside the cleanup CLI is unsafe.
- A process crash during directory publication may leave an unused complete
  generation. It is still recoverable and can be pruned later; the previous
  dataset.yaml pointer and older readers remain intact.
- This is dataset-cache consistency, not true transactionality for concurrent
  source labeling edits. A source session changing while copied could still
  produce a coherent but temporally mixed snapshot; editing live recordings
  needs a separate upstream recording/label locking protocol.
- Windows lock semantics differ from POSIX shared flock and require testing.
- Merge/review **PR #18** before this stacked update. No unrelated files or
  project-wide configuration schema changes.
