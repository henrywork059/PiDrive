# PiServer 0_4_23 — R43 adaptive status polling and bandwidth

## Request / acceptance
Implement `docs/roadmaps/PiDrive_Refinement_Roadmap.md` R43 for the active PiServer web control UI. Preserve the existing single-in-flight, backend sequence-verified JPEG preview; extend **read-only** status refresh with idle-tab throttling, bounded backoff, server-reported status-generation freshness and immediate focus recovery. Do **not** change the 60 ms manual controller tick, deadman, motor STOP, safety heartbeat/watchdog, saved settings, or panel docking.

## Baseline / anti-rollback
- Direct parent is unmerged R36 PiServer **draft PR #50**, `update/piserver-0_4_22-responsive-verification`, head `2a3281d04f060a1ef6171cdd1d0915150ddeb93c`. R43 branch: `update/piserver-0_4_23-r43-adaptive-polling`. Must review R35 #46 and R36 #50 before merging R43.
- Read actual entry `PiServer/server.py`, live `piserver/app.py` and `piserver/web/static/app.js`, R30 `preview_freshness.js` and template. Reviewed latest R36 notes **0_4_22**, previous three **0_4_21** (R35 accessibility/STOP), **0_4_20** (R31 applied settings), **0_4_19** (R30 preview sequence and freshness). No older ZIP overlay or file replacement.
- Preserve PiServer 0_4_x bug-fix series; no changes to component runtime configuration, camera/model/motor services, CSS, manual pad, themes, or saved layout.

## Cause
Visible idle PiServer tabs used an unconditional 800 ms `setInterval(pollStatus)` (75 status reads/minute) even if there was no camera, recording or manual motion. The old implementation skipped hidden reads and preserved sequence-checked camera streaming, but it did not slow visible idle reads or back off repeated status failures, and could not display the backend's status generation time.

## Exact files and behavior
1. `PiServer/piserver/web/static/app.js` — remove only the `setInterval(pollStatus, 800)` interval. Add a self-scheduling, **single-flight** status `setTimeout` loop. Active (backend `camera_preview_live`, recording, AI run, active manual pad/keys) uses **800 ms**; visible idle uses **2,500 ms**. Failed requests retry exponentially with **8,000 ms** cap. Hidden ticks make **no HTTP status request**, inspect visibility every 5 seconds, and immediate focus return schedules a request at 0 ms. A `statusPollingReady` guard prevents a redundant status read during startup. Server timestamp is shown in existing status banner tooltip, without new layout.
2. `PiServer/piserver/app.py` — additive `server_status_at_ms = int(time.time()*1000)` in `/api/status` (backend-generated UNIX epoch milliseconds). Advance `APP_VERSION` **0_4_22 → 0_4_23** to ensure updated cache-busted assets. No backend safety or motor loop edits.
3. `PiServer/tests/test_adaptive_polling_r43.cjs` **new** — Node unit/safety checks using the actual browser scheduling function for idle, active, hidden, retry, motor tick, preview sequence and modeled request rate.
4. `PiServer/README.md` — R43 behavior, modeled before/after table, actual Network verification guidance.
5. `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_23.md` — this note.

## Verification actually performed
- Parsed the **exact live new GitHub** `app.js` through a JavaScript parser (`new Function` syntax-only): **passed**.
- Executed the **live GitHub scheduling policy function** against 4 independent deterministic scenarios: 800 ms active, 2500 ms idle, 5000 ms hidden, bounded retry to 8000 ms; **4/4 passed**. This was a controlled JavaScript policy execution, not a browser HTTP request simulation.
- A broader **22/22 source-level integration/anti-rollback audit** across R43 PiServer/CustomDrive/PiSD passed, including unchanged motor tick, sequence-based preview, original safety paths and additive server timestamps.
- New `test_adaptive_polling_r43.cjs` is committed but **not run as a standalone Node test file against the live branch** (GitHub workspace is not locally mounted). Raspberry Pi camera/webbrowser/end-to-end motor tests and measured network captures **not performed**. Do not claim throughput or physical performance certification.
- Direct-parent GitHub compare/removed/unrelated file checks must be completed before draft PR creation.

## Deterministic before/after request-rate profile (modeled only)
One visible idle browser tab, fast successful status responses, no user actions, 60-second steady-state: baseline 60,000/800 = **75 status requests/min**; R43 60,000/2,500 = **24 status requests/min**, a **68% reduction**. Active visual status remains 75/min. Hidden periodic status requests become zero; existing camera JPEG loop remains separately governed by R30 single-in-flight/retry logic. Actual HTTP counts can differ due to network latency, overlapping operator requests and tab scheduling.

## Limits / release gate
- Back-end `server_status_at_ms` is generated when status is constructed; client shows backend clock time as information, not a synchronized latency proof. Preview freshness remains determined by backend JPEG sequence/live state and monotonic client age.
- Status refresh is **not** the motor safety/control heartbeat. Existing `STEP_INTERVAL_MS=60`, fail-safe stop on hide, runtime watchdog, auth/CSRF and control endpoints are untouched.
- Before merging: `node --test PiServer/tests/test_adaptive_polling_r43.cjs`, run whole PiServer suite, capture 60-second Network request counts+bytes (active, idle, hidden, resumed) on the Pi, verify live control remains responsive, no stale preview falsely marked live, E-stop works even when tab hidden; inspect R35/R36 focus/layout and Save/Apply. No PR merged without authorization.
