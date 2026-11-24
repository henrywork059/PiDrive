# piTrainer 0.11.5 — R38 preview memory and throughput

## Request
Implement roadmap **R38 — piTrainer preview memory and throughput**. Measure small/medium/large dataset load latency and peak RSS, then address only demonstrated bottlenecks. Prevent stale frame image/steering/speed pairing during rapid navigation, keep scaled preview cache bounded, retain original Qt overlay/flip/image semantics and do not regress R37 selection scope or older accepted features.

## Exact baseline and anti-rollback
- Branched from unmerged piTrainer **R37 PR #53**, `update/pitrainer-0_11_4-r37-selection-scope` (piTrainer `0.11.4`); do **not** merge R38 before its R37 parent. Main remains at `c615c73032d62daa23ec0fe302d1cfe6049428c3`, with R33–R36 other-component branches still open.
- Reviewed actual launcher `piTrainer/main.py`, `AGENTS.md`, image preview, `utils/image_utils.py`, `services/data/record_loader_service.py`, `preview_service.py`, visibility service, Data-page selection/filter/playback wiring, and existing overlay service/road geometry. Reviewed R37 0_11_4 and previous three notes: 0_11_3 (model manifests), 0_11_2 (atomic metadata edits), and 0_11_1 (synthetic source grouping).
- Preserve read-only `QTableView`/`QAbstractTableModel`, source-row maps, R37 scope strip, default sort, Validation → Edit in Data → Return, the Image Preview's click/drag control mapping, 450 ms queued metadata edits, session loading/metadata and source path schemes, synthetic `aug_flip_lr` handling and overlay redraw. No config/user recordings changed.

## Measurements and decision (performed)
Measured the exact current **record-loader and filtering code**, using the uploaded `piTrainer_0_11_0.zip` file whose Git blob SHA `6f24a07f52e009639377b7752fbfb8ae17ad3fcb` matches the live R37 GitHub `record_loader_service.py` **byte-for-byte**. Measurements are on Linux, Python 3.13, using generated 426×240 RGB JPEGs, unique frame names linked to the same sample bytes, PiSD-style `labels.jsonl` rows, pandas and one fresh process per count:

| Frames | `load_records_dataframe` | `build_filtered_dataframe` | Peak **whole-process RSS** |
|---:|---:|---:|---:|
| 250 | 15.69 ms | 1.71 ms | 96.02 MiB |
| 2,500 | 107.85 ms | 6.53 ms | 98.39 MiB |
| 10,000 | 501.21 ms | 23.47 ms | 112.22 MiB |

These are one-run controlled synthetic fixture observations, not claims about full DataPage load time, actual Windows hardware or native Qt preview decode. Peak process RSS includes interpreter/pandas/Pillow/fixture creation; only load and filter durations isolate named operations. **Conclusion:** no evidence justifies changing loader logic or existing session/path semantics in R38.

A separate source audit found `utils/image_utils.py` previously cached **96 QPixmaps regardless of pixel memory**. For 32-bit decoded displays, theoretical cache pixel cost is 96×W×H×4: ~189.8 MiB at 960×540, ~337.5 MiB at 1280×720, ~759.4 MiB at 1920×1080. This unbounded *byte* risk justifies extending the existing LRU rather than inventing a second cache.

## Root cause
The existing preview rendered each `set_record()` selection synchronously. Multiple rapid Up/Down/frame selections could each decode, transform and paint a full image even if superseded before the event loop settled. Selection changes also updated steering/speed controls before replacing the old image, allowing transient old-image/new-label pairings. An older 120 ms resize timer could redraw after a later selection. The cache was entry-bounded but not byte-bounded, and keyed only by path/target size/flip, so replacing a source image at the same path could reuse stale pixels.

## Files and precise behavior
1. `piTrainer/piTrainer/utils/image_utils.py` — **reuses** its original LRU of unannotated, scaled pixmaps; preserves original `QPixmap(path)`, `QTransform().scale(-1,1)` and `Qt.KeepAspectRatio`/`SmoothTransformation`. Adds **64 MiB estimated decoded-pixel budget AND prior 96-entry cap**, evicts least-recently-used scaled copies, does not store oversized images (still returns them to caller), and exposes optional cache stats/clear helper. Cache keys additionally include `mtime_ns` and source file byte size; a deleted/overwritten file is not served from a stale cache key. A changed signature of the same path/size/flip replaces its earlier cached copy. **Overlays are not cached**: existing painters create detached per-record pixmaps, preserving correct labels even if the source image repeats. This is a cache accounting limit, not an OS/GPU memory limit.
2. `piTrainer/piTrainer/panels/data/image_preview_panel.py` — retains existing 450 ms metadata-write debounce and 120 ms resize debounce; adds a single-shot **0 ms selection render timer** for the next event-loop turn. On selecting a new record, cancel both queued render timers, increment generation, clear old pixels *before* synchronizing steering/speed controls, and schedule one latest-record render. Clearing the preview cancels both timers. `_render_preview` snapshots the current frame's stable identity, render generation and labels, then rejects stale decode/render results both before and after drawing overlays. Overlay changes and slider label edits increment generation, cancel queued selection paints, and immediately redraw the latest record via the existing painter functions. Resize and selection renders are coalesced without affecting overlay scale, source `aug_flip_lr`, image geometry, or metadata commit queue. **QPixmap and QPainter stay on the GUI thread**, not a worker thread.
3. `piTrainer/tests/test_preview_r38.py` (new) — **15 cases**: 13 standard-library mock/AST tests for byte/item budgets, LRU hits, source overwrite/delete, flip key separation, empty/oversized handling, rapid A→B→C navigation coalescing, old-image clearing, pending cancel, stale nested selection and flipped overlay path; plus 2 optional real offscreen PySide6 pixel orientation and overlay-size checks.
4. `piTrainer/tests/benchmark_preview_r38.py` (new) — CLI for fresh-process synthetic 250/2,500/10,000 dataset loads, load/filter timings, peak process RSS where supported, and optional actual **offscreen PySide6 QPixmap** navigation benchmarking. No user recordings are modified; optional Windows psutil provides peak working-set metrics where available.
5. `piTrainer/piTrainer/version.py` — `APP_VERSION 0.11.4 → 0.11.5` and `PATCH_VERSION piTrainer_0_11_5`; no new version scheme.
6. `piTrainer/README.md` — documents measurements, cache semantics, benchmark commands and the Qt validation requirement.
7. `piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_5.md` — this note.

## Verification actually performed
- The two modified production source files were recreated locally from the original, byte-identical uploaded baseline and the same targeted changes; final Git blob hashes of the **compiled and tested** local files matched the exact connected GitHub R38 branch: `utils/image_utils.py` = `8da16e31737b58169fb83657c2c325d9965f8ed2`, `panels/data/image_preview_panel.py` = `062df7b3e8937ecb7fa7a75f1e31b7a4a0307cc9`.
- `python -m compileall -q` succeeded for both changed local production files.
- **13/13** local hardware-free tests passed on those exact source blobs: byte-budget eviction, existing 96-item cap, cache hit/move to end, flip distinction, file replacement/removal, oversized entries, cache clear, queued navigation coalescing, label/image atomic switch, cancellation after clear, nested later-selection stale-result rejection, and flip propagation.
- The **15-case committed Python test file was added but has NOT been executed end-to-end from GitHub**; its two optional real Qt tests are unrun because PySide6 is not installed in the container. The benchmark runner in the PR also has not yet been executed on the Windows target, and no actual native QPixmap RSS/pixel measurements were made.
- Current GitHub comparison against the R37 PR parent and unrelated-component/rollback checks are reported in the draft PR.

## Limits / release gate
- Byte-cost estimates are based on QPixmap width×height×at least 32-bit depth; actual Qt platform allocations, GPU backing, transient original full-resolution decodes and displayed/painted images are **not** covered by the 64 MiB cache budget. A single enormous source image still decodes once to display it. The existing GUI thread may still block briefly on one slow uncached image, though superseded **queued** frames are skipped.
- File signatures use `mtime_ns + size`, not a content checksum; a file replaced with identical size and preserved timestamp could still hit the old cache. This avoids hashing every preview frame during navigation.
- Before promoting R38, run `cd piTrainer && python -m unittest discover -s tests -v`; then run `python tests/benchmark_preview_r38.py --counts 250 2500 10000 --qt-preview` on the Windows PySide6 workstation. Inspect scaled/overlaid and horizontally flipped images, high-DPI resize, rapid Up/Down + playback, Validation→Data round-trip identity, R37 counts, queued metadata edit commit, and actual RSS over repeated navigation. Do not claim these full integration/hardware checks have passed without executing them.
