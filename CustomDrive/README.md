# CustomDrive

## R48 passive GUI and Mission 1 preflight (GUI 0_3_19 / Mission 1 0_5_29)

The general **Status / System** panel and the separate Mission 1 **Setup**
panel now each contain a collapsed, read-only **Startup preflight**.
Page load and **Refresh checks** call only `GET /api/preflight` in the
respective Flask app, using already-created service status getters and
`shutil.disk_usage`. No physical or simulated motor/servo command, camera
start, AI model load, mission start, configuration save or external network
probe is part of the preflight handler.

Seven checks show mode, camera, model/AI, GPIO motor adapter and safety,
**arm servo** backend (disabled / simulated / physical-but-unproven),
disk space, and browser-to-server HTTP reachability. A Mission 1 camera
not yet created before route completion is reported as **deferred/expected**
rather than silently started. The selected model is also distinguished
from one actually loaded later during mission stages. Even while a mission
runs, the response mode remains `simulation-running` vs
`hardware-adapter-running` to avoid false physical readiness. Existing
R44 Grip/Drop-off trigger positions, STOP, rearm and Save-before-Start
guards remain authoritative.

Targeted tests, from repo root:
```bash
cd CustomDrive
python -m unittest discover -s tests -p 'test_preflight_r48.py' -v
cd ..
node --test CustomDrive/tests/test_preflight_gui_ui_r48.cjs
node --test CustomDrive/tests/test_preflight_mission_ui_r48.cjs
```
On real hardware, verify both pages at mobile and desktop widths, status
during motor/arm simulation and missing I2C, deferred camera, missing
Mission model, low disk and 401/403/500. Run previous R33/R35/R36/
R43/R44/R45/R46/R47 checks. No cross-component UI stylesheet or config
migration is introduced.

## R47 failed-action tracing (GUI 0_3_18 / Mission 1 0_5_28)

The general GUI and separate Mission 1 web app each install the same
component-owned **failure-only** Flask response hook. Failed `/api/*`
mutations return `correlation_id`, `operation`, and `X-Correlation-ID`
while keeping the existing HTTP status and output keys, including
`ok:false`/HTTP 200 and unsuccessful `saved:false` readbacks. A server log
line `api_mutation_failure id=<ID> operation=<name> http_status=<status>`
is generated once per failure, without the request body or credential/
file-path values. No shared runtime module with PiServer/PiSD is required.

GUI Drive Apply / AI Deploy and Mission 1 Save / Start / Upload / Arm pose
display short error guidance with expandable **Error details**. Details
show only the ID, server operation, HTTP status and bounded code. The
frontends do not display arbitrary backend exception or request-body text
for traced failures. R44's grip/drop-off readback confirmation and Mission
Start/servo Save guard, R43 polling, R35 STOP, R33 timeline and user configs
are unchanged. This is not a background telemetry exporter.

Tests (repo root):
```bash
python -m unittest discover -s CustomDrive/tests -p 'test_request_trace_r47.py' -v
node --test CustomDrive/tests/test_request_trace_ui_r47.cjs
```
Validate real Flask/GUI and Mission 1 pages on a Pi, failed Deploy and
failed Start/Save, invalid config, 401/403 and unavailable server behavior,
physical STOP, and consistency between displayed ID and one log entry.

## R45 UI token contracts (GUI 0_3_16 / Mission 1 0_5_26)

Use [UI_DESIGN_TOKENS.md](UI_DESIGN_TOKENS.md) for new GUI or Mission 1
panels. Their palettes and status meanings remain component-owned, and
`theme.js`, existing CSS, saved style preferences, servo controls, timeline,
and trigger guides are untouched. Run
`node --test CustomDrive/tests/test_ui_style_tokens_r45.cjs` from repo root.
This is a style-policy/drift-check update, not a theme migration.

## Mission 1 trigger threshold ruler and live readout (0_5_25, R44)

Mission 1's existing camera preview now shows a small **100 / 50 / 0%**
vertical frame scale, with separate **green Grip** and **amber Drop-off**
horizontal guides. The numeric readout immediately beneath the preview
remains legible on narrow displays. The scale is the existing U24 convention:

- **100% = frame top**, **50% = frame center**, **0% = frame bottom**.
  For frame height `H` pixels and threshold fraction `p` between 0 and 1,
  the browser guide position is `H × (1 − p)` pixels down from the top;
  Mission 1's center-origin gate remains `H × (p − 0.5)`.
- The two independent backend settings are
  `arm.grip_trigger_y_ratio` and `arm.dropoff_trigger_y_ratio`.
  Existing saved values are retained and normalized to 0–1; the form,
  readout and guide support **0.1%** precision (matching the backend's
  three-decimal stored ratio). The 0% value now also remains 0 when the runtime computes the actual pickup
  and drop-off gate (previously a falsy-value fallback turned it into 30%).
- Editing **Grip trigger Y** moves **only the grip guide**; editing
  **Drop-off trigger Y** moves **only the drop-off guide**. Before saving,
  dashed overlay guides and the readout explicitly say **Preview only**
  and show both values last reported by the server. No HTTP request or
  motor command is sent by a field edit.
- **Save Mission 1 Config** reads back the new normalized values from
  both `config` and `status.config` in the save response. The readout
  switches to **Saved on server** only when those values agree; the
  live status panel and guides then use that same returned server status.
  A failed/mismatched save retains the unsaved preview. Start Mission 1
  and Load arm pose no longer proceed after an unconfirmed config save.

Existing fixed 16:9 frame geometry, AI/object boxes, Mission 1 timeline,
U24 gate direction and separate drop-off logic, U28 safety/rearm, R35/R36
accessibility/layout, and R43 adaptive polling are not redesigned. GUI
`0_3_15` is unchanged; Mission 1 alone advances `0_5_24 → 0_5_25`.

Launch from the verified entrypoint:

```bash
cd CustomDrive
python run_mission1_stage_test_demo.py
```

Regression checks from the monorepo root:

```bash
node --test CustomDrive/tests/test_trigger_guides_r44.cjs
cd CustomDrive
python -m unittest discover -s tests -p 'test_trigger_runtime_r44.py' -v
```

Before promoting the draft, verify actual Mission 1 HTTP config readback
and live preview at 0/50/100%, change one field while the other stays
constant, confirm failure leaves the old effective threshold, and
physically check motor/arm STOP, trigger transitions, preview width and
phone readability. The committed tests and actual Pi hardware checks
must be executed on an appropriate workstation.

## Adaptive browser polling and bandwidth (R43)

Both CustomDrive web apps retain their original backend mission/motor rates
and safety authority. Only **read-only browser refresh** scheduling changes.

The **GUI** uses 1,500 ms status refresh during manual movement, active
camera preview or in-flight control; 4,000 ms when idle; no periodic
HTTP status reads in hidden tabs. Errors retry exponentially up to 10 s;
the first visible-tab refresh is immediate. The backend includes the additive
`server_status_at_ms` (actual response generation time) shown as a
status-banner tooltip. Its existing single-in-flight, sequence-checked,
decoded JPEG loop is preserved.

**Mission 1** keeps active status at 600 ms and active annotated-image
requests at 250 ms, but idle status slows to 2,500 ms and inactive frame
checks to 2,000 ms (no frame HTTP request without the live AI camera phase).
Hidden tabs make **no status/frame HTTP requests**. Returning to the tab
resumes both immediately. Status/frame errors use bounded retries
(8 s / 4 s); one annotated image request is allowed at a time, with
a 1-second timeout that abandons a stalled image load before retry.
`server_status_at_ms` is displayed as an observation tooltip; it does
not modify mission timing or camera generation frequency.

| Modeled one-tab status traffic | Before | After idle | During active |
| --- | ---: | ---: | ---: |
| GUI | 40/min | 15/min | 40/min |
| Mission 1 | 100/min | 24/min | 100/min |
| Mission 1 frame requests, fast successful response | 240/min | 0/min without live frame | 240/min |

These are **formula-based maximum schedule rates**, not captured network
measurements; request duration, failures and visibility affect observed
rates. Real live-frame cadence can be lower due to backpressure.

Run `node --test CustomDrive/tests/test_adaptive_polling_r43.cjs` from
the monorepo root. Before merging, compare 60-second browser Network traces
for active/idle/hidden/resumed states with actual camera/motor and Mission 1
operation, including failed image requests. The control heartbeat, safety
STOP, R33 stage timeline and R35 keyboard hold-release must remain intact.

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
