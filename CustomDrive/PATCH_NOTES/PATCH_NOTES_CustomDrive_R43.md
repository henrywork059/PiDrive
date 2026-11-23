# CustomDrive GUI 0_3_15 + Mission 1 0_5_24 — R43 adaptive polling and bandwidth

## Request / scope
Implement R43 from `docs/roadmaps/PiDrive_Refinement_Roadmap.md` for the separate CustomDrive GUI and Mission 1 web apps: adaptive inactive tab polling, bounded status/frame retry and server-reported status generation freshness. Keep **600 ms active Mission 1 status**, **250 ms active Mission 1 frame target**, and **1500 ms active GUI status**; no motor/arm/mission/control loop or safety heartbeat changes. Provide modeled before/after request-rate profile and live release checklist.

## Exact baseline / anti-rollback
- New R43 branch `update/customdrive-r43-adaptive-polling` is directly from **R36 draft PR #51**, `update/customdrive-r36-responsive-verification`, head `329ac3a5ad77dc2bc302cabd61e74cd9dd59a8af`. That stack retains R35 PR #47 and R33 PR #43 and is not merged. Do not merge R43 before those parents.
- Read actual entry points `CustomDrive/run_custom_drive_gui.py` (forwards to `run_custom_drive_web.py`) and `run_mission1_stage_test_demo.py`, GUI web app `custom_drive/gui_control_app.py`, `gui_web/static/app.js`, Mission 1 `mission1_session_app.py`, `mission1_web/static/app.js`, and respective templates. Reviewed latest patch note **R36**, previous three **R35**, **R33**, **R31**, plus R30 preview freshness semantics.
- Respect separate version lines: GUI **0_3_14 → 0_3_15**, Mission 1 **0_5_23 → 0_5_24**, no invented project-wide version; exact component folders and persistent settings unchanged.

## Root cause
- GUI visual status was read from Flask every 1,500 ms even when visibly idle (40 requests/min). It used a single-in-flight boolean but no idle throttle, hidden pause, bounded status backoff, or immediate focus status catch-up.
- Mission 1 status was polled every 600 ms (100/min) regardless of mission running, despite no need for frequent quiet idle refresh. Its annotated image loop checked every 250 ms even outside the AI live phase and scheduled its next timer immediately when assigning an `img.src`, risking an additional image request before the previous one completed. A 800 ms timeout cleared the local in-flight flag without actually abandoning the stalled image source.
- Neither status API exposed a concrete generation timestamp that the UI could show as server-origin freshness.

## Files changed / exact behavior
1. `CustomDrive/custom_drive/gui_web/static/app.js` — convert only visual status `setInterval(...1500)` to a single-flight self-scheduling timer: **1500 ms** while manual controls, preview, or control command are active, **4000 ms** when idle, zero hidden status HTTP reads. Failure retry exponentially capped **10000 ms**. Immediate refresh on visibility return. Existing decoded-JPEG preview backpressure/freshness, motor controls and visibility-triggered manual release untouched. Existing banner tooltip displays actual backend `server_status_at_ms`.
2. `CustomDrive/custom_drive/gui_control_app.py` — additive `payload['server_status_at_ms'] = int(time.time()*1000)`; GUI version **0_3_15**. This only changes a read-only status field, not motor authorization.
3. `CustomDrive/custom_drive/mission1_web/static/app.js` — status **600 ms active** / **2500 ms idle** / no HTTP hidden; up to **8000 ms** retry cap. Frame refresh **250 ms** during active AI phase, **2000 ms** quiet checks without image HTTP requests, zero hidden HTTP; frame failure retry capped **4000 ms**. Enforce one image request in flight: schedule next frame after load/error/timeout, abort stalled image load by clearing src after 1000 ms, ignore superseded callbacks using request ID, recover both status/frame immediately on visible-tab return. Existing status timeline, grip/drop-off marker geometry and motion routines unchanged. Show backend timestamp as viewer stats tooltip.
4. `CustomDrive/custom_drive/mission1_session_app.py` — additive read-only `server_status_at_ms` in status payload and Mission 1 version **0_5_24**, with no modification to state transitions, safety/arm/motor loops, servo timing or route.
5. `CustomDrive/tests/test_adaptive_polling_r43.cjs` **new** — deterministic Node checks of actual GUI/Mission scheduling function behavior, retry caps and modeled request rates; audits one-in-flight frame and hidden tab safety.
6. `CustomDrive/README.md` — usage, simulated rate table, actual network profiling and release checks.
7. `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R43.md` — this note.

## Verification performed
- JavaScript syntax parse **passed** against exact live GitHub copies of both changed browser files (`new Function`, compile only).
- Executed actual GitHub scheduling functions with 12 deterministic cases: GUI 1500 active/4000 idle/5000 hidden/10000 retry cap; Mission 600 active/2500 idle/5000 hidden/8000 retry cap; Mission frame 250 active/2000 idle/5000 hidden/4000 retry cap. **12/12 passed**, separately from the committed Node suite. No browser request or motor command was issued during these policy executions.
- A **22/22** live-source safety/integration review across three component R43 branches passed: verified existing control and STOP hooks untouched, GUI/Mission server timestamps, 250 ms frame target, single-flight marker, visible re-entry and version lines.
- Committed `test_adaptive_polling_r43.cjs` with 8 tests but it has **not been executed end-to-end as a standalone file against the GitHub working tree**. Real Mission 1/GUI browser network counts, Raspberry Pi camera, object detector, motion, servo, and stop/watchdog tests **not performed**; full Python/Node tests also pending. Do not claim actual network, frame throughput or physical safety measurements.
- Direct-parent compare and file removals/outside component checks to be performed before opening PR.

## Before/after request-rate profile (modeled steady state; not measured)
- **GUI status**: old 60000/1500 = 40/min; R43 visible idle 60000/4000 = **15/min** (62.5% fewer), active remains **40/min**.
- **Mission 1 status**: old 60000/600 = 100/min; R43 visible idle 60000/2500 = **24/min** (76% fewer), active remains **100/min**.
- **Mission 1 annotated frame**: active 60000/250 = **240 maximum scheduled requests/min** before/after, *assuming instantaneous success*; real load+decode/backpressure reduces it. Inactive no live-camera frame HTTP is requested. Hidden status/frame HTTP requests become zero after outstanding in-flight request abort/completion.
- Backoff stretches intervals after failure and avoids runaway retries. Actual concurrency, browser timer clamp and latency change observed rates; nothing here is a measured physical benchmark.

## Limits / release gate
- Server timestamps describe response generation on the backend clock; do not infer RTT without clock synchronization. Frame freshness still depends on real image load/error and server-reported mission phase; no fabricated frame timestamps.
- Status cadence is **presentation-only** and never governs motor watchdog, arm hold, mission cycle frequency, safety heartbeat or rearm. New hidden-tab activity does not issue a motor drive command; existing STOP/release handlers are preserved.
- Run `node --test CustomDrive/tests/test_adaptive_polling_r43.cjs`, then full CustomDrive tests. On a Pi, measure 60-second GUI and Mission 1 active/idle/hidden/resume Network traces including image payload bytes, slow/stalled JPEG, remote disconnect/recovery. Confirm mission stage remains live while visible, Stop/E-stop/rearm remain prompt, R35 keyboard hold and R36 responsive layouts, R33 timeline, R31 settings save/retry, R30 preview freshness, U28 safety and real servo timing. Do not merge without user approval.
