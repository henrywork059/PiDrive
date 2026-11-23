# CustomDrive Mission 1 0_5_21 — R33 server-observed mission progress timeline

## Request summary
Implement R33 of `docs/roadmaps/PiDrive_Refinement_Roadmap.md`: a compact, read-only timeline showing the **current mission step, last completed step and last failure**. Show the actual stages the Mission 1 server enters, not a mandatory fixed seven-step route. Make camera boot, model loading, no-frame waits and servo pose settling legible without adding or changing automatic mission transitions.

## Baseline, actual entry point and prior notes
- **Direct baseline:** merged GitHub `main`, commit `c615c73032d62daa23ec0fe302d1cfe6049428c3` after PRs #9–#42 merged. No older branch or ZIP restored.
- Actual standalone Mission 1 Flask runtime is `CustomDrive/custom_drive/mission1_session_app.py` (`create_mission1_session_app()`); its web assets live under `CustomDrive/custom_drive/mission1_web/`. This is separate from `CustomDrive/run_custom_drive_gui.py` and `run_custom_drive_web.py` (the general driving GUI).
- Inspected the current Mission 1 state machine, U22 failure latching, U24 pickup/drop-off triggers, 0_5_20 safety/rearm, 0_5_19 performance, U29 replay, R30 preview, and R31 saved-settings notes. Preserves the accepted mission state and operator rearm semantics, active model/arm behavior, and safe stop-before-grip/release.

## Cause / previous gap
The original Mission 1 browser showed raw `phase`, `mission_state`, `arm_sequence`, logs, and many summary cards, but did not display sequential progress or the latest successful transition. A 600 ms poll could miss rapid server-side stage switches, while waits for a camera frame, model load, and arm-settle delay could look like an unresponsive mission. Inferring all possible steps from the current phase alone would misrepresent skipped or repeated stages.

## Changed and added files
- `CustomDrive/custom_drive/mission1_session_app.py`: add a bounded, process-local, **read-only** `mission_timeline` payload on the existing `GET /api/status`. Observe the phase from the existing `_record`, status reads, and actual paired state assignments; explicitly capture stop-before-pose settling. Reset history only when a new session successfully starts. Version marker **0_5_20 → 0_5_21**, on the existing Mission 1 version line. No mission-stage assignment, command, camera setup, rearm rule, model operation, or persisted config is changed.
- `CustomDrive/custom_drive/mission_timeline.py` **new**: thread-safe bounded observation helper with an explicit map of actual `current_phase` strings. Supports route, camera start, model load, waiting for frame, pickup search/alignment, grip/pose, lift, drop-off transport/alignment, release, and reverse reset. Stages are appended **only when observed**, not manufactured by a preset checklist. Tracks most recent completed transition, interrupted/failed stage, failure reason and source stage. Can show repeated pickup cycles; ignores unrecognized phases. No hardware imports.
- `CustomDrive/custom_drive/mission1_web/static/mission_timeline.js` **new**: pure view projection from backend-owned `mission_timeline`; no guessed stage order on the client. Bounded text and validated status values.
- `CustomDrive/custom_drive/mission1_web/static/app.js`: compact timeline renderer integrated into existing status refresh; HTML-escapes all status-derived content. No new fetch interval, control request or action.
- `CustomDrive/custom_drive/mission1_web/templates/index.html`: timeline above the summary telemetry cards and camera image, with current/last-completed/failure summary.
- `CustomDrive/custom_drive/mission1_web/static/styles.css`: small responsive horizontal activity markers (green completed, blue current, red failed, amber interrupted) using existing theme variables.
- `CustomDrive/tests/test_mission_timeline.py` **new**: 24 Python unit cases for actual backend stage observations, terminal states, skipped stages and repeated cycles.
- `CustomDrive/tests/test_mission1_timeline.cjs` **new**: 22 deterministic frontend projector cases.
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_R33.md` — this note.

## Precise behavior
- **Actual stage only:** `recent_steps` is the bounded sequence of stages observed by the backend; no silent `Route → Search → Align → ...` completion assumptions. Model/camera startup and frame waits have their own explicit entries.
- **Last completed:** a previous observed step is marked completed only on a forward stage progression (or confirmed complete outcome). An interrupted camera wait, backwards search, operator STOP, failure, and idle tabs do not create false completions.
- **Arm settling:** stop-for-grip and stop-for-release are observed before settling. The latest backend arm-sequence note and `detail` appear below the timeline.
- **Failure:** U22 `failure_reason`, `failure_stage`, `last_error` populate a diagnostic failure item; stop remains interrupted and no rearm occurs automatically. The failed stage remains visible even if the worker has stopped.
- **Repeated mission loops:** after release/reset the next observed pickup search is identified as the next cycle without pretending the mission has ended. Release or reverse-reset is counted completed when the next pickup cycle is actually entered, including when reverse is disabled. History is bounded; new sessions reset progress only after passing the original start guards.
- **Control safety:** no new motion paths, no additional stage transitions, no new motor permission, no generated servo/grip confirmation, no configuration migrations, no change to mission reports, and no modifications to GUI/headless components. A successful servo pose is still unverified by a grip sensor.

## Verification actually performed
- Final client helper and full Mission 1 browser script parsed using the V8 JavaScript runtime. A lightweight fake-DOM renderer smoke check verified that untrusted backend HTML text is escaped.
- A failed status poll flags the displayed timeline as disconnected/stale until a successful backend status response, without making any control request.
- **22/22** frontend timeline projection cases executed using a CommonJS-compatible V8 adapter.
- Backend Python unit test source added but **not executed** in the connected GitHub environment.
- GitHub compare against main and unchanged main-file spot checks listed in draft PR.

## U22/U28 regression compatibility
Some existing hardware-free recovery tests deliberately instantiate `Mission1SessionContext.__new__` without its constructor and mock `_record`. The timeline observer therefore checks for the optional tracker and becomes a no-op for those minimal contexts. Normal initialized mission sessions still construct and reset the tracker. No existing test fixture or behavior was rewritten.

## Known limitations / next steps
Backend phase observation is process-local and is not a reboot-persistent audit log; the existing U22 mission JSON report remains separate. The last completed step reflects successful progression *to* a new phase, not independent camera/servo sensor verification. Faster changes are captured at explicit backend state assignments, but this patch does not add a real-time event stream. Physical camera/arm/motor validation, Flask/browser integration testing, and full CustomDrive suite must be run before promoting from draft.
