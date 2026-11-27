# PiDrive — Two performance optimization updates

**Proposed 2026-11-27. Update 1 implementation CI-qualified at 4ee5e302; workload acceptance in progress. Update 2 remains planned.**
Planning reference: main at `a31cbff0a0802fb246f053b281ddc42cef367713`; consult the live HEAD again before implementation. The completed 56/56 proposal, 9/9 batch software roadmap remains closed. This is an additional two-milestone performance track, not a reclassification of old requirements or a stable-release authorization.

## Scope and baseline

Active components only: PiSD (candidate 0.11.45, `PiSD/PiSD.py`), PiServer (0.4.53, `PiServer/server.py`), piTrainer (0.11.32, `piTrainer/main.py`), as recorded in [release-candidate handover](RELEASE_CANDIDATE_HANDOVER.md). Verify current candidate versions, latest plus preceding three component patch notes, current CI and package ancestry before any edit. Do not assign version numbers until implementation warrants them and merged/pending versions are reconciled. Keep PiBooter, CustomTrainer, CustomDrive and legacy piCar unchanged.

Optimize CPU-seconds per useful unit of work, peak/steady RSS, allocation churn, input/output traffic, processing latency and measured energy per workload. Do not simply reduce work quality, change camera/recording settings, lower safety-critical frequency, or shorten source code at the expense of correctness. Prioritize single-line or localized changes when profiling and equivalence tests justify them.

### Existing source evidence (live main, static inspection)

| Component | Existing mechanism / candidate hotspot | Relevant file |
|---|---|---|
| PiSD | Cached JPEG/metadata accessor already exists (~634); frame copies/color conversion (~1040–1123), JPEG encoding (~1166). Verify encoding demand and ownership, do not implement a second competing cache. | `PiSD/pisd/services/camera_service.py` |
| PiSD | Interpreter allocation (~941) is already present; inference input resize, cast/normalize and quantization (~1062–1084), output conversion (~1101–1172), inference dispatch (~1195–1199). Profile repeated allocations and single-example Keras call overhead. | `PiSD/pisd/services/ai_drive_service.py` |
| PiServer | Preview resize and JPEG (~486–488), direct/cached snapshot handling and frame copies (~661–721). Preserve raw versus preview semantics and recording freshness. | `PiServer/piserver/services/camera_service.py` |
| PiServer | Interpreter allocation (~147), preprocess resize/float normalization and quantization (~223–253), invoke (~293). | `PiServer/piserver/services/model_service.py` |
| Web | PiSD AI status timer (~1479) and visibility/readiness logic (~1865–1899); PiServer visibility sync (~2198), preview-health timer (~2207), preview fetch (~1600). Already partly optimized; only remove proven redundant background work. | `PiSD/pisd/web/static/js/ai_mode.js`, `PiServer/piserver/web/static/app.js` |
| piTrainer | tf.data input already batches and prefetches AUTOTUNE (~63); image resize (~36). Validation already uses batched predict (~45). Measure memory/throughput tradeoff before altering. | `piTrainer/piTrainer/services/train/dataset_service.py`, `piTrainer/piTrainer/services/validation/validation_service.py` |

Line numbers are orientation aids, not stable contracts; static evidence is not proof of a performance defect. Older uploaded archives were inspected for context, not used to replace live source.

## Update 1 — Eliminate redundant computation (low-risk, measurable)

**Goal:** Reduce idle and active CPU cost while preserving outputs and responsiveness. Implement in component-owned commits, with actual performance evidence rather than formatting-only one-liners.

- [ ] **P1.1 Measurement harness.** Add repeatable opt-in profiling and benchmark workloads using existing simulation/fixture infrastructure; record CPU time (user + system), wall time, RSS, frame/encoding/inference counts, queue depths, bytes transferred and p50/p95 latencies. Profile cProfile and tracemalloc separately from timed runs; RSS captures native allocations that tracemalloc misses. Instrument counters at bounded cadence, disabled or lightweight in normal operation.
- [ ] **P1.2 Camera demand and reuse.** In both runtimes, verify one capture owner; reuse immutable encoded preview per frame/settings generation across viewers; skip duplicate resize/JPEG and overlay recomputation when safe and when no consumer demands preview. Preserve existing caching and invalidation, raw frames, snapshot/recording consumers, camera timestamps, color orientation, start/stop lifecycle and current settings. Avoid copies only where buffer lifetime, contiguity and ownership are proven; keep safety/recording isolation copies.
- [ ] **P1.3 Web and idle work.** Coalesce noncritical status refreshes; prevent overlapping requests; suspend only hidden/background presentation polling, pause unnecessary DOM/canvas updates when values are unchanged, refresh on visible/focus and resume cleanly on reconnect. Preserve current visibility-aware preview logic, authorization, command lease/watchdog, STOP delivery and all manual control timing. No control polling or heartbeat reductions.
- [ ] **P1.4 Inference micro-optimizations.** Benchmark avoiding redundant dtype/layout conversions, caching shape/dtype/quantization constants per model generation, using reusable owned preprocessing buffers and in-place normalization when equivalent. Preserve interpreter ownership and one-time allocation. Compare direct Keras inference call with predict for batch 1 only if actual compatible Keras models and output contracts support it. Test prediction equivalence, model switching, failure paths and freshness independently.
- [ ] **P1.5 Trainer presentation/data review.** Reuse bounded thumbnails/decoded images by path, modification identity, orientation and overlay settings; invalidate after edits; avoid unchanged plot/table resets and repeated dataframe scans; lazy visible-row rendering and coalesced refreshes where current implementation still repeats work. Preserve stable frame identities, filter/sort, edit/undo, shortcuts, docking, playback and selected row.
- [ ] **P1.6 Regression and deliverable.** Resolve existing CI failures first. Add deterministic tests for work counters, idle demand, cache invalidation, viewer fanout, concurrent recording, model swaps, visibility/reconnect and safety. Run all applicable existing Linux/Windows, native Qt, web visual, integration and package checks; report before/after paired measurements and rejected experiments. No new release candidate for audit-only changes.

### One-line / small-change candidates (illustrative, not unconditional patches)

| Candidate | Intended benefit | Condition |
|---|---|---|
| `np.asarray(image, dtype=np.float32)` instead of conversion chains | Avoid redundant allocations | Confirm dtype/layout and source ownership; this does not guarantee zero copies. |
| `array *= np.float32(1.0 / 255.0)` | Avoid allocating a second normalized array | Only with an owned writable float32 array; test rounding and model outputs against baseline. |
| `cv2.setNumThreads(n)` | Avoid competing OpenCV/inference worker pools | Benchmark n=1,2,4/default per device; configure once at startup, not per frame; retain best safe result. |
| `Interpreter(model_path=path, num_threads=n)` | Right-size LiteRT/TFLite CPU worker pool | Verify supported runtime signature, benchmark 1/2/4/default and maintain model compatibility. |
| `if frame_seq == last_processed_seq: ...` | Avoid duplicate optional preview work | Key by frame and settings generation; never use this to bypass stale-frame detection or control safety. |
| `if (!document.hidden) ...` | Avoid hidden tab presentation work | Presentation only; abort/coalesce requests safely and refresh immediately when visible. |
| `dataset.prefetch(1)` | Bound input buffering | Compare to existing AUTOTUNE under identical seeded workloads; not universally faster. |
| `logging.getLogger(__name__).debug("frame %s", seq)` | Avoid eager log formatting | Preserve required faults/audit logging; only if hot path uses eager formatting. |
| `collections.deque(maxlen=N)` | Bound optional diagnostic history | Only nonessential telemetry; never truncate recording labels or safety/audit data that must persist. |

Prefer explicit small helpers when a one-liner obscures ownership or error handling. No code golf, global GC disabling, unsafe buffer aliasing, uncontrolled thread expansion, blind dependency upgrades, or changing semantics just to reduce line count.

## Update 2 — Resource-aware processing and sustained efficiency

**Prerequisite:** Update 1 has a reproducible before/after report, safety gates are green, and latest accepted source is reconciled. Continue on top of that state; do not restore earlier copies. Focus on the remaining expensive operations, not merely new settings or another audit.

- [ ] **P2.1 Camera pipeline.** Evaluate Picamera2 main + low-resolution stream for preview and/or inference when hardware and format support allow; avoid repeated software resize and format conversion. Compare supported native/hardware encoder path versus software JPEG and current HTTP contract. Do not assume hardware encoding on all Pi models, force a transport migration, alter training image quality or change camera calibration. Keep current fallback; test camera reopen, consumer changes, recording, timestamps, freshness and pixel/color correctness.
- [ ] **P2.2 Bounded work scheduling.** Use bounded producer/consumer buffers and latest-frame semantics for optional presentation/inference only where existing freshness/ordering contracts permit. Prevent stale backlog, cap cache bytes and surface drops. Recording must preserve its accepted sampling and label synchronization, with explicit overload reporting rather than silent discard. No unbounded queues or blocking motor STOP on optional work; ensure stale frame still stops autonomous operation and rearm remains explicit.
- [ ] **P2.3 AI runtime resource tuning.** Benchmark explicit LiteRT/TFLite thread counts and supported delegates on target Pi, using same model/input and checking p95 latency/CPU-seconds/inference and steering/throttle parity. Evaluate optional INT8 export only with representative data, calibration, output contract, model-family checks, actual end-to-end validation and explicit acceptance. Default model and safety thresholds unchanged. Keep unsupported-device fallback and reason reporting.
- [ ] **P2.4 Trainer scalable data pipeline.** Profile large session load, data review, training and validation. Evaluate streaming batches, bounded prefetch/parallel-map, disk or byte-bounded caches of deterministic transforms, worker thread loading and incremental table models; never cache random augmentations in a way that freezes per-epoch randomness. Preserve dataset split, seed, ordering, source IDs, labels, preprocessing, export provenance and model metrics. Compare CPU/GPU utilization, epoch time, peak RSS, prediction equivalence and UI responsiveness.
- [ ] **P2.5 Optional resource profile.** If results justify it, offer Balanced (existing settings/semantics) and Low Resource modes for *noncritical* workloads: preview quality/frequency, telemetry refresh, cache budget and training thread/prefetch limits. Make effective settings visible, persistent and clamped; preserve unknown keys. Restore immediately without restart where safe; no automatic changes to recording/AI input, STOP, control lease, motor limits or safety frequency. Explicitly distinguish idle/preview profiles from driving.
- [ ] **P2.6 Sustained and physical acceptance.** Perform long-run soak and supervised Pi tests with wheels raised or otherwise safely secured, then owner-approved controlled physical tests. Monitor temperature, throttling, RSS slope, CPU, frame freshness, p95 latency, recording counts and emergency STOP under load. Measure energy (Wh) using external meter under matched conditions; software temperature/CPU is not energy measurement. Complete full regression and changed-file package gates. Keep baseline visual archives and remaining native accessibility/EXE/physical acceptance distinct; no stable promotion/deployment without explicit approval.

## Benchmark protocol and proposed acceptance targets

Targets are planning goals, **not measured improvements**. Establish attainable baseline on actual device before committing thresholds; record misses, tradeoffs, and explicitly approved exceptions. Use fixed camera source/resolution/FPS, model checksum, dataset and split, quality, software/hardware versions, thermal/power conditions, workload duration, client count and seed. Same workload and outputs, warm-up, at least 5 paired runs; median and dispersion, p95 latency. Use matched randomized order where practicable; report CPU-seconds, peak and steady RSS, not just wall time or machine-wide CPU%. Separate cold startup, idle and steady state. CI asserts deterministic counts/equivalence, not flaky wall-time thresholds; dedicated hardware benchmark tracks resource budgets.

| Metric | Update 1 goal vs original baseline | Update 2 cumulative goal vs original baseline |
|---|---:|---:|
| Pi runtime idle CPU-seconds/min | -25% | -40% |
| Pi runtime active CPU-seconds/processed frame or inference (report both separately) | -10% | -20% |
| Peak RSS for matched large trainer workload | -10% | -25% |
| Trainer data review p95 latency | -15% | -25% |
| Matched Pi workload energy (external meter) | Baseline and measurement if available | -15% |
| Safety-critical latency, dropped recording data, model/label correctness | No regression | No regression |

Measure each runtime separately (do not assume they run together). Workload matrix: startup/model load; idle no viewers; one and two preview viewers; manual and recording; AI steady and simultaneous preview/recording; disconnect/reconnect and frame starvation; trainer small/large fixed datasets, playback/filter/edit/validation/training/export; 30–60 minute repeated runtime soak and longer hardware soak if warranted. Report absolute and relative values, p50/p95, correctness results, and rejected optimizations. No percentage savings may be advertised without evidence.

**Nonnegotiable gates:** existing STOP, watchdog, lease, access control, stale camera stop/rearm, motor limits and AI safety behavior; no regression of saved configs, model family/checksum, training/export/recording data, UI baseline or accessibility. Maintain approved 105 web PNG reference at ba2420536b733659c6cb4796490cdb38f8d31914; compare instead of silently replacing. Preserve all component boundaries, version conventions and package checks. Actual Pi/Windows/desktop, assistive technology and energy acceptance remain unverified until run on the relevant environment.

## Research and upstream documentation

Reviewed 2026-11-27. Use installed dependency versions when applying APIs. Recommendations are experiments, not guaranteed gains.

1. Python deterministic profiler and allocation tracing: https://docs.python.org/3.12/library/profile.html and https://docs.python.org/3/library/tracemalloc.html — locate expensive call paths and Python allocation churn; pair with process RSS.
2. NumPy copies/views: https://numpy.org/doc/stable/user/basics.copies.html — avoid unnecessary buffers only with verified ownership and stride/layout.
3. OpenCV thread controls and timing: https://docs.opencv.org/4.10.0/db/de0/group__core__utils.html — tune thread budgets per target, rather than blindly maximizing.
4. Google LiteRT performance best practices: https://developers.google.com/edge/litert/conversion/tensorflow/build/best_practices — profile operator costs, thread count, quantization and delegates against accuracy and device behavior.
5. Raspberry Pi Picamera2 upstream configuration and source: https://github.com/raspberrypi/picamera2/blob/main/picamera2/picamera2.py and https://github.com/raspberrypi/picamera2/blob/main/picamera2/encoders/encoder.py — low-resolution stream and encoder configuration are platform-dependent; inspect supported formats and hardware before enabling.
6. TensorFlow data performance: https://www.tensorflow.org/guide/data_performance and https://www.tensorflow.org/guide/data_performance_analysis — balance parallel map, caching, prefetch and memory usage; measure rather than assume AUTOTUNE is optimal for constrained devices.
7. Qt model/view: https://doc.qt.io/qtforpython-6/overviews/qtwidgets-model-view-programming.html — incremental fetch and model updates for large tables.
8. MDN Page Visibility API: https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API — presentation scheduling when tabs are hidden, not a replacement for server-side control safety.

## Delivery rules

Two substantial milestones; separate component-owned source commits and patch notes, patch-only archives if requested. Update 1 is low-risk compute elimination plus a benchmark baseline; Update 2 is measured pipeline/scheduling work plus sustained resource verification. Avoid documentation-only candidate increments and unnecessary micro-patches. Before each milestone, read AGENTS.md, the latest plus three previous patch notes, actual code and current CI; preserve the approved screenshot reference and all user-local data. Each delivered patch must include exact changes, baseline and candidate hashes, commands, test results, benchmark artifacts and hardware limits. No merge of new implementation branches, stable promotion, deployment or inactive-component changes authorized by this planning document.

Related: [roadmap progress](PROGRESS.md), [completed development schedule](DEVELOPMENT_SCHEDULE.md), [handover](RELEASE_CANDIDATE_HANDOVER.md), [acceptance gate](../stabilization_acceptance.md).

## Update 1 workload qualification — 2026-11-27

Application source candidate `4ee5e3022e0cbd4031d26fd99edf306d147a9441` (PiSD 0.11.46, PiServer 0.4.54, piTrainer 0.11.33) passed Linux 45997141640 and Windows 45997141553 (5/5 jobs), all three forward package dry runs, 78 browser cases, and exact operation-level benchmarks. [Evidence and limits](https://github.com/henrywork059/PiDrive/pull/88#issuecomment-7218138993). Keep these version markers and source unchanged during the workload qualification.

New opt-in `tools/benchmark_camera_workloads.py` and dedicated CI workflow compare the original main `14c57c990ff0f9bae2003e4e8aa552d17a4227c7` and the exact qualified application SHA, in fresh subprocesses per revision/component/pair, five alternating pairs, idle / one / two viewers / recording / inference / concurrent / reconnect. Real service threads, writers and multipart generators; PiSD simulation and fake PiServer request device, copying synthetic interpreter, TCP loopback body transfer. Report process CPU, sampled RSS and per-process high-water RSS, encode/publish and capture counts, recording and inference counts, frame age and bytes; no physical power, real detector throughput or whole-system claim. Timing goals remain provisional; do not close P1.1/P1.2/P1.6 until actual results and parity reviewed. No speculative runtime edits, new component version or release authorization.
