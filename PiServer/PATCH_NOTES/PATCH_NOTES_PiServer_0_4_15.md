# PATCH NOTES — PiServer_0_4_15 (U23 runtime performance diagnostics)

## Request summary
Expose bounded camera, model and control-loop latency percentiles and process CPU diagnostics through the existing protected status API. This is the PiServer portion of cross-component roadmap U23.

## Root cause
PiServer previously reported FPS and current frame age but not comparable latency distributions for capture, model resize/inference and hardware motor updates. Sampling and percentile computation must avoid continuous logging, unbounded memory and additional dependencies.

## Files changed
- `PiServer/piserver/core/latency_metrics.py` (new)
- `PiServer/tests/test_latency_metrics.py` (new)
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py` (version 0_4_15)
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_15.md` (new)

## Exact behavior
- Camera captures sample frame acquisition/preview-loop work and count capture misses, in a bounded `performance` helper.
- Model inference samples RGB preprocessing/resize, TFLite invoke/tensor exchange and output postprocessing; nonfinite/invalid inference results increment failure counters.
- Controller loop samples actual motor-apply calls and work per active control iteration. Existing manual deadman and motor emergency-stop paths remain unchanged.
- `GET /api/status` now includes `performance_diagnostics.controller`, `.camera`, `.model` and `.camera_frame_age_s`; all original status keys remain. The existing access-control middleware protects this route in LAN mode; test doubles without a performance method are tolerated.
- All samples use fixed-size 120-item deques, finite nonnegative elapsed durations, nearest-rank p50/p95 generated only on status inspection, and a CPU process percentage sampled at most once per second. No SD writes, extra timing threads, dependency or settings changes.
- Real queue wait and sensor-to-actuator total delay are not claimed without timestamps at those boundaries; missing stage samples are not displayed as zero.

## Anti-rollback review
- Built directly on live draft **PiServer 0_4_14 PR #16**, stacked on PR #15, #14 and #9.
- Reviewed notes 0_4_14, 0_4_13, 0_4_12, and 0_4_11. Preserve cross-runtime hardware ownership lock, dynamic model tensor-shape preflight, LAN token authentication, CSRF protections, emergency stop and manual watchdog, settings and UI layout.

## Verification actually performed
- New metrics helper and tests: `python -m unittest discover -s tests -p test_latency_metrics.py -q` in the locally available PiServer package: **10/10 passed**. Includes deterministic fake clocks, bounded percentiles, invalid sample rejection, CPU sampling and concurrent readers/writers.
- The Git-uploaded helper and test blob hashes match the exact local test files.
- Current PR #16 implementation source was inspected and modified at unique matching anchors. **Full stacked Flask tests, live Pi physical testing and performance budget benchmarking were not performed**.

## Known limits
- Process CPU percent is not device-wide CPU load and may exceed 100% on multi-core hardware; it is intentionally sampled only when status is requested.
- The camera capture duration includes selected encoding/preview work and is not strictly raw sensor exposure delay. Independent end-to-end trace/queue measurement and real Pi load tests are future work. Merge/review PR #16 first.
