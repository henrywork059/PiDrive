# CustomDrive

CustomDrive provides mission-flow and manual-control applications built on shared runtime abstractions for simulated and live Pi operation.

## Mission 1 latency and CPU diagnostics (0_5_19, U23)

The existing Mission 1 `/api/status` `pipeline` object preserves FPS and
cycle-time values and adds bounded `performance` (controller-loop work,
motor apply and camera-frame age before inference) and
`detector_performance` (preprocessing/resize, inference and postprocessing).
Each sampled stage exposes p50/p95/last milliseconds across at most 120
observations; counters track stale/failed frames and model failures when
observed. Process CPU percent is sampled on status reads, not continuously,
and is the sum of process core consumption rather than entire-system load.

No verbose per-frame logging, SD-card writes, arm/config updates, motor logic
changes or browser layout changes are introduced. The accepted grip/drop-off
thresholds, explicit mission-failure states, and non-verified grip labeling
remain intact. A missing stage indicates no measured samples, not zero delay;
queue waits are not claimed without a real queue. No performance target is
assumed until real Raspberry Pi 4 measurements are available.

## Current documented entry points

From `CustomDrive/`:

- Demo runtime: `python run_custom_drive_demo.py`
- GUI web control: `python run_custom_drive_gui.py`
- Manual web mode: `python run_custom_drive_manual.py`
- Mission 1 web mode: `python run_custom_drive_web.py`
- Headless runtime launcher: `python run_custom_drive_headless.py`

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Recommended Python: **3.11**.

Pi-only features depend on hardware/runtime libraries (camera/GPIO/TFLite). In non-Pi environments, fallback/sim behavior may be used depending on selected mode.

## Mission 1 runtime safety and reports (0_5_18)

Mission 1 has bounded autonomous target searches and fail-closed stage outcomes.
A stopped/failed mission **does not resume on its own**: inspect the failure
reason and use a new explicit Start action only after resolving the cause.
A default search stage is limited to 20 seconds and camera-frame age is
limited to 2 seconds. Both limits may be adjusted in the existing
`config/mission1_session.json` under `mission.search_timeout_s` and
`mission.frame_timeout_s` (safe normalization clamps apply).

The live Mission 1 status now exposes `mission_outcome`, `failure_reason`,
`failure_stage`, `target_loss_count`, `grip_confirmation` and
`mission_report_path`. Failure reasons include `frame_stale`,
`target_lost`, `arm_unavailable` and `retry_exhausted`. A failed
grip-ready, grip/lift or release **servo pose** prevents progression to
the next motion stage.

**Grip confirmation is not available with the current arm interface.**
A successful servo position command is reported as
`pose_applied_unverified`, meaning the object is *assumed held*, not
physically confirmed. Do not use the report as proof of a grasp.

After a stopped or failed session, a compact JSON report is saved under
`CustomDrive/mission_reports/mission1_<session-id>.json`, without
overwriting previous reports. Reports include the stage, structured
failure reason, assumed held object class, and bounded recent events,
but not credentials or the full runtime settings file. They are for
local diagnostics, not training data.

Existing stop-before-grip/stop-before-release, nonblocking pose display,
class 1/2 → drop-off 3/4 routing, trigger coordinates (**100% = top,
0% = bottom**), manual motor calibration, and saved arm positions remain.
The actual pickup stage reads the Grip threshold; the drop-off stage
reads the separate Drop-off threshold. Failed stages do not trigger a
blind autonomous reverse/back-out: a future operator-approved recovery
mode is needed before moving without fresh perception.

Before deploying to Raspberry Pi hardware, run the Mission 1 simulation
tests and verify stale-camera, lost-target and arm-failure scenarios
with wheels raised. The current motion stop is software-controlled; an
independent motor-controller watchdog remains a separate safety task.

## Important configuration files

- `config/runtime_settings.json`
- `config/run_settings.json`
- `config/mission1_session.json`
- `config/manual_control.json`
- `config/servo_test.json`
- `config/dual_servo_test.json`

## Manual GUI web control

Run:

```bash
python run_custom_drive_gui.py
```

Typical URL:
- local: `http://127.0.0.1:5050`
- LAN: `http://<pi-ip>:5050`

Features include:
- camera preview
- drag-pad/drive controls
- Drive Settings and Style Settings overlays
- arm-control buttons using `config/manual_control.json`

## Mission 1 note

Mission-session UI version marker is defined in:
- `custom_drive/mission1_session_app.py`

When updating docs for Mission 1 behavior, verify this marker and parser behavior in `mission1_tflite_detector.py` to avoid stale release-note assumptions.

## Bug-prevention reference

Before modifying detection, overlay, or session UI behavior, read:
- `../BUG_PREVENTION_NOTES.md`


### U28 explicit mission-fault rearm (0_5_20)

The generic web GUI and standalone Mission 1 web application add `GET /api/safety/status` and `POST /api/safety/rearm` with JSON `{"confirm":true}`, plus an additive `safety` field on existing `/api/status` responses. A failed mission remains latched after Stop; click **Rearm after fault** only after checking the cause. Rearm stops and resets/zeros controls but **does not restart driving**. Start is a separate action. This is a process-local web safety contract; hardware/arm safety and headless scenarios require Pi-side validation.
