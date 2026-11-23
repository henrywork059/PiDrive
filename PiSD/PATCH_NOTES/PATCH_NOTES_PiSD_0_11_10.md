# PATCH NOTES — PiSD_0_11_10 (U23 runtime performance diagnostics)

## Request summary
Add bounded p50/p95 latency and CPU observations to the PiSD camera and AI status paths, without changing capture FPS, preview FPS, prediction FPS, or motor safety. This is the PiSD component of cross-project roadmap U23.

## Root cause
Before this update, PiSD exposed latest/average camera loop and JPEG encode times and a single last AI inference duration, but lacked bounded comparative latency distributions, per-stage model costs and a low-overhead process CPU diagnostic. Unmeasured queue delays must not be represented as zero latency.

## Files changed
- `PiSD/pisd/core/latency_metrics.py` (new)
- `PiSD/scripts/test_latency_metrics.py` (new)
- `PiSD/pisd/services/camera_service.py`
- `PiSD/pisd/services/ai_drive_service.py`
- `PiSD/pisd/__init__.py` (version 0.11.10)
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_10.md` (new)

## Exact behavior
- Camera status adds a `performance` object with sampled capture-loop and JPEG encode time distributions; empty or failed JPEG/capture increments `dropped_frames`.
- AI status adds its own `performance`: JPEG decode, resize/array preparation, new inference, correction/safety postprocess, actual motor updates, and active control-loop work. Reused predictions are counted separately rather than falsely registered as zero-millisecond inference; AI inference failures and stale-frame latch outcomes have counters.
- Every stage tracks only the latest 120 finite, nonnegative durations using fixed-size deques. A status read calculates nearest-rank p50/p95 and the last sample. Unsampled stages are omitted.
- The helper samples process CPU time / elapsed wall time at most once per second **when status is read**, with an explicit multi-core caveat. It does not run a thread, write logs, alter settings, or set performance thresholds.
- Existing status fields are retained. Queuing is not timed because the current route has no explicit timestamped task queue; no speculative end-to-end actuation delay is claimed.

## Anti-rollback review
- Based on the live GitHub **PiSD 0.11.9 draft PR #20**, which stacks on PR #12 (0.11.8).
- Inspected latest notes 0.11.9, 0.11.8, 0.11.7 and 0.11.6. Preserves offline recording recovery, AI camera-staleness latch, Snapshot/live preview and the accepted four AI output tabs, independent three-rate FPS, recording labels, and visual-only overlay and persisted settings.
- Does not edit PiSD recordings, config files, model files, or legacy PiCar.

## Verification actually performed
- New bounded metrics helper and its test module were installed in the PiSD package locally; `python -m unittest discover -s scripts -p test_latency_metrics.py -q`: **10/10 passed**, including fake-clock CPU timing, p50/p95, bounded memory and concurrent writers.
- New helper and tests have exact Git blob hashes matching those locally executed files.
- Live branch source was inspected and modified using exact, unique source anchors. **Full PiSD runtime tests, live Pi 4 camera/motor testing and hardware latency measurements were not performed** in this environment.

## Known limits
- Distribution samples are process-local, reset on restart, not correlated with other PiDrive components; CPU % is not whole-device utilization.
- Stale frame counters are AI failure occurrences, not a physical dropped-frame estimate.
- Capture-to-actuation trace IDs, true queue waits, a shared per-frame correlation clock and hardware performance targets remain follow-up. PR #20 must be reviewed/merged before this stacked change.
