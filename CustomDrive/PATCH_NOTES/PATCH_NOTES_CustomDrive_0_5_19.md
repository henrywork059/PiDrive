# PATCH NOTES — CustomDrive_0_5_19 (U23 Mission 1 latency diagnostics)

## Request summary
Add bounded, in-memory Mission 1 inference and control timing distributions and process CPU usage to the existing live status output while retaining all prior mission safety and UI behavior. This is the CustomDrive portion of cross-project roadmap U23.

## Root cause
Existing Mission 1 status exposed FPS and last cycle duration but not a latency distribution distinguishing detector input preparation, inference, postprocessing, actual motor calls and active control-loop work. Cached frame age was available to safety logic but not as a rolling diagnostic.

## Files changed
- `CustomDrive/custom_drive/latency_metrics.py` (new)
- `CustomDrive/tests/test_latency_metrics.py` (new)
- `CustomDrive/custom_drive/mission1_tflite_detector.py`
- `CustomDrive/custom_drive/mission1_session_app.py` (APP_VERSION 0_5_19)
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_19.md` (new)

## Exact behavior
- The model detector records RGB resize/preprocessing, TFLite invoke/tensor transfer and YOLO output processing. The active Mission 1 session records frame age **before** inference, motor-apply duration and active loop work.
- Already-protected stale frame failures increment `stale_frames`; the existing failure-state transition, motor stop, manual restart and arm roles are unchanged.
- Existing `/api/status` `pipeline.fps` and `pipeline.cycle_time_ms` remain. Additional `pipeline.performance` and `pipeline.detector_performance` expose up to 120 samples per stage, p50/p95/last milliseconds, fixed counters, and a lazily sampled process CPU percent.
- Unknown/unmeasured stage samples are omitted. The telemetry does not pretend to measure total capture-to-actuation latency, and queue wait is not fabricated. No logging, config persistence, unbounded buffers, extra dependencies, motor output changes or new UI panels.

## Anti-rollback review
- Built on live **CustomDrive 0_5_18 draft PR #21**, stacked on PR #11 (0_5_17 trigger guides).
- Inspected notes 0_5_18, 0_5_17, 0_5_16 and 0_5_15, preserving separate grip/drop-off guides and thresholds (100% top / 0% bottom), stop-before-grip/release and live camera preview while arm poses progress, motor calibration, structured mission failures and report creation.

## Verification actually performed
- New metrics helper/tests: `PYTHONPATH=. python -m unittest discover -s tests -p test_latency_metrics.py -q`: **10/10 passed**, including bounded fake-clock distributions, concurrency and CPU timing.
- The exact Git blob hashes of the new helper and tests match local executed files.
- Existing current Mission 1 source was inspected and modified using unique matching anchors. **Full Flask browser runs, real TFLite inference and Raspberry Pi motor/arm hardware testing were not performed**.

## Known limits
- The process CPU percentage measures process CPU / elapsed time, not whole-system usage, and can exceed 100% on multiple cores. Status snapshot sampling is lazy, not a dedicated CPU monitor.
- Frame age before inference is not actual end-to-end frame-to-motor latency; per-frame correlation and queue delay remain future work. The old generic MissionController demo runtime is unchanged. PR #21 must be reviewed before merging this stacked update.
