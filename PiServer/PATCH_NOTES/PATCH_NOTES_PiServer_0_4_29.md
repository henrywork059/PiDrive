# PiServer 0_4_29 — U21 autonomous camera freshness

## Cause and scope
Batch 1 audit found that auto_steer and autopilot infer from get_latest_frame even if cached or disconnected. The control loop had no camera age guard. This patch adds a bounded, monotonic sample age policy for the two actual camera-dependent algorithms. Manual, Stop and the existing manual lease remain unchanged.

## Changes
- services/camera_service.py: publish raw-frame capture timestamp under the same lock as the raw image; read atomic frame/time only when capture is running and live; invalidate timestamp on start.
- algorithms/auto_steer.py and autopilot.py: add compute_from_frame, preserving their existing public compute and output interpretation.
- services/control_service.py: wait at zero for an initial fresh frame for up to 0.75 s; latch on missing/stale frame after readiness or grace, hard stop, reject inference output if the exact sample expired during compute. Keep capture processing on while camera fault is latched to verify recovery. Explicit rearm requires fresh sample and returns to manual at zero. Add status fields. No config changes.
- tests/test_control_service.py: deterministic missing/stale frame, recovery without auto restart, exact-frame inference and late-result rejection cases.
- piserver/app.py: version 0_4_28 -> 0_4_29.

## Verification / limits
Reviewed actual server launcher, latest 0_4_28 and previous 0_4_27/26/25 notes, current camera/control and algorithm sources. Patch only on latest integrated active stack. CI must execute tests on exact commit; no physical camera or motor test. Monotonic timestamp is conservative capture-start age, not sensor exposure time. The in-loop check rejects stale results but does not guarantee timely motor stop if inference blocks indefinitely; that needs a separate independent output watchdog and physical acceptance. Existing model fallback semantics are unchanged. Keep draft until review.
