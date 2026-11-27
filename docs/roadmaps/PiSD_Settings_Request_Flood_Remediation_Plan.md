# PiSD — Settings request flood remediation and emulator qualification

**Status: Proposed, P0 runtime performance regression; no implementation or acceptance claimed.**
Owner Windows report: 2026-11-28, 00:36:48–00:37:18 local time. Source examined: main `3a2a575698a2b89ebd148fbbcaa3d33a8b773c21`, PiSD 0.11.48; the same suspected defect was inspected at `8f593778eb461f8515f6c12c5fce936dc64cb301`. The user's exact local commit was not printed; do not assume it. Reconcile current main and pending PRs before implementation.

## 1. Observed incident and diagnosis

The supplied Windows console excerpt contains 1,001 HTTP requests: 1,000 HTTP 200 and one HTTP 503. Breakdown:

| Route | Count |
| --- | ---: |
| GET /api/settings | 699 |
| GET /api/camera.jpg | 159 |
| GET /api/status | 62 |
| GET /api/pisd/status | 58 |
| POST /api/control/manual | 11 |
| POST /api/control/heartbeat | 6 |
| GET /api/camera/fps-stats | 4 |
| POST /api/runtime/restart | 1 |
| POST /api/track | 1 |

Settings GETs occur in three logged one-second buckets: 75 at 00:36:48, 512 at 00:36:49, 112 at 00:36:50. The excerpt begins during the burst; do not infer its full duration or sustained rate. Virtual motor messages show nonzero throttle and changing steering. Camera responses resume after one 503 at 00:37:06 around restart. HTTP 200 alone does not establish successful application-level control, actual vehicle displacement, correct frame contents, safe STOP, or release acceptance.

Static root-cause hypothesis (confirmed code path, not yet reproduced in a browser): [panel_presentation_global.js](../../PiSD/pisd/web/static/js/panel_presentation_global.js) listens to storage changes for `pisd.panelPresentation.v1` and `pisd.runtimeSettings.v2`, invokes `loadFromBackend()`, then calls `save(panel)`. That function writes the runtime key with a fresh `saved_at` even when presentation data is unchanged. Two same-origin browsing contexts (e.g. embedded PiSD page plus direct PiSD tab) can exchange storage events and sustain redundant GETs. Storage events do not fire in the writing document itself. The emulator controller and PiSD use different ports/origins; do not presume those two origins alone trigger the loop. Confirm actual browser initiators, context count, and alternative sources before changing code.

Relevant consumers: [manual_drive.js](../../PiSD/pisd/web/static/js/manual_drive.js), [panel_presentation.js](../../PiSD/pisd/web/static/js/panel_presentation.js), [settings_tab.js](../../PiSD/pisd/web/static/js/settings_tab.js), [ai_mode.js](../../PiSD/pisd/web/static/js/ai_mode.js), [manual_lease.js](../../PiSD/pisd/web/static/js/manual_lease.js), and [emulator controller](../../PiSD_Emulator/web/assets/app.js). The controller has separate 500 ms status and 180 ms camera intervals; profile independently rather than treating those normal requests as the settings flood.

## 2. Implementation sequence

| ID | Priority | Deliverable | Status |
| --- | --- | --- | --- |
| SF-01 | P0 | Reproduce and attribute: capture request initiator/route/time, context count, storage events, inflight peak, exact commit and operating mode. Compare standalone, embedded, two same-origin tabs, and both embedded + direct tab. | Open |
| SF-02 | P0 | Break feedback cycle: separate applying confirmed presentation from user-authored persistence; no timestamp mutation or network echo for unchanged or remotely received settings. Ignore unrelated runtime-key changes when presentation is unchanged; use relevant storage payload safely. Preserve server-confirmed settings and cross-context synchronization. | Open |
| SF-03 | P0 | Single-flight noncritical settings reads per context; deduplicate identical writes; bound refresh/retry behavior with stale-response protection and explicit invalidation on genuine saves. Preserve explicit load/save/apply/reset readback and failure reporting. | Open |
| SF-04 | P0 | Safety regression: preserve command lease, heartbeat 250 ms cadence, 0.85 s expiry, STOP priority, hide/blur/release semantics, camera fault latch, AI output guards and authentication. Never throttle or cache control mutations with settings reads. | Open |
| SF-05 | P1 | Add deterministic JS regression and real multi-context browser tests, including slow/failed reads, simultaneous saves, reload/restart, hidden/visible transitions, and preservation of current panel settings and manual/AI workflow. | Open |
| SF-06 | P1 | Emulator live qualification: Windows and Linux, actual embedded and direct PiSD pages, steering/throttle -> motor mapping -> pose -> changed decoded image, camera settings, track change, restart, STOP, recording continuity and workspace isolation. | Open |
| SF-07 | P2 | Quantify CPU, RSS, request counts/bytes, latency and frame freshness before/after using matched workloads. Improve optional access-log readability only after eliminating the traffic; retain errors, safety and diagnostic visibility. | Open |

## 3. Proposed measurable acceptance gates

These are engineering targets, not achieved results. Report any deviation with evidence rather than silently relaxing them.

- Reproduce the pre-fix burst or document why it cannot be reproduced, with browser initiator evidence. Then run matching post-fix scenarios for at least 60 seconds, excluding initial load from the steady-state window.
- After startup settles, zero autonomous settings GETs caused solely by cross-context storage events or manual steering; no self-sustaining reads/writes. For explicit reload/save/reconciliation, document a bounded request budget (target <= 2 settings GETs per context per logical operation, excluding deliberate explicit readback/retries where justified). At most one noncritical settings GET in flight per context.
- Genuine settings changes propagate to both contexts without losing unrelated settings or overwriting newer confirmed values; unchanged values produce no new storage timestamp and no redundant writes. Explicit backend readback, error feedback and persistence survive restart.
- Test standalone, embedded, direct plus embedded, two tabs, two browser windows, and same-origin multi-context rapid settings changes. Capture console/network errors and compare relevant settings before/after. Check unauthorized requests and failed backend reads; do not hide defects by filtering logs.
- Verify STOP with direct zero-output evidence and no stale queued nonzero command after STOP, lease expiry, lost focus, hidden tab, failed heartbeat, camera fault and restart. Use existing safety timing contracts; report actual timings. Confirm no physical GPIO access in emulator.
- Matched workloads: idle, sustained keyboard/drag, preview, concurrent tabs, recording and restart. Keep camera resolution/FPS, model, track, simulation speed, recording options, device and workload duration matched. Capture settings GET counts per context and total, response bytes, CPU seconds, peak/steady RSS, p50/p95 HTTP/control latency, observed frame sequence/age and decoded image changes. Separate actual measurements from expected effects.
- Target zero settings-flood traffic during steady driving, no regression of useful throughput, camera freshness, safety or settings semantics. Capture browser screenshots and machine-readable request/latency counts; include failures and exact CI/artifact links. No physical Raspberry Pi or hardware acceptance implied.

## 4. Reconciliation and release controls

- This is a targeted follow-on defect under [Performance Optimization](PiDrive_Performance_Optimization_Plan.md) P1.3 and [UI/UX Improvement 2](PiDrive_UI_UX_Improvement_2_Plan.md), and a blocking qualification item for [emulator E02/E03/E05/E06](../../PiSD_Emulator/ROADMAP.md). Do not change existing historical 56/56 and 9/9 accounting or claim completion of an emulator requirement solely from this log.
- At planning time open concurrent PRs included #93 (Performance 2.5), #94/#95/#97 (UI2), #98 (integration), #99 (unified release candidate), and #92 (UI2 foundation). Verify their live state and exact HEAD/CI before edits. Avoid parallel competing settings implementations; integrate once into the currently authorized forward development line. Resolve existing failures before claiming acceptance.
- Inspect current source, latest plus previous three PiSD patch notes, current version/accepted baseline and package ancestry. Follow AGENTS.md and stabilization acceptance; no duplicate version allocation, no stable promotion or deployment authorization from this plan. Do not overwrite current user-local settings/models/recordings or the emulator workspace. Preserve actual launchers, original PiSD HTML, existing motor/camera/AI service semantics and UI improvements. No unrelated component changes.
- Run relevant PiSD JS/Python/API/safety suites and emulator browser/service suites, including existing `PiSD_Emulator/scripts/test_emulator.py` and `PiSD_Emulator/scripts/test_frame_browser.py` (verify their invocation and dependencies at implementation HEAD). Verify exact CI on final implementation SHA; independently inspect screenshots and exported evidence. Document any missing Windows/Linux/hardware verification.
- Actual implementation must include component patch notes, changed-file packaging where applicable, and measured evidence. Allocate the next candidate only after reconciling merged and pending versions; no version bump for this plan. Do not merge or promote runtime changes without applicable owner authorization.

## 5. Interim local workaround

Stop the previous server safely, close duplicate PiSD tabs/windows, relaunch `python PiSD_Emulator/run_emulator.py --open-browser` from repository root, and use a single embedded PiSD context. This may reduce the hypothesized trigger; it is not a verified fix. Do not reset browser/runtime settings or disable STOP/heartbeat to suppress traffic.

**Next action:** SF-01 through SF-04 as a consolidated priority bug-fix milestone, then real browser regression and matched performance qualification before further emulator feature expansion. This document records the observed defect and proposed acceptance criteria only; no code changes or test PASS claims.


## Update B — implementation checkpoint (2026-11-28)

Stacked on exact qualified integration parent a4b9496b9c5d302b9a574e7e69984d8686b13b4f, independent of release PR #99. Retain existing provisional version; no version bump, merge, tag, stable promotion or deployment. The original plan and SF IDs remain authoritative.

| ID | Checkpoint status |
| --- | --- |
| SF-01 | Deterministic production-JS reproduction: bounded 251 GETs/252 writes before stop; original Git blob a9bad7b5330fdbda30d5ff17f470768c09689517. Actual browser initiator evidence pending. |
| SF-02 | Implemented candidate: storage notifications apply relevant current presentation data without a GET or write; identical values do not restamp. Six local deterministic tests green at exact candidate blob 64521544d00a932796d8b86abcb210cc46499a33. |
| SF-03 | Presentation reads single-flight, 3.5s timeout, stale response protection; existing page-specific explicit reads/mutations retained. Full all-page request-budget qualification pending. |
| SF-04 | Control/STOP/lease and API code unchanged; exact regression and live virtual STOP evidence pending. |
| SF-05 | New six-case Node regression registered; real multi-context test added with genuine save/readback and 60-second quiet interval. Exact browser CI pending. |
| SF-06 | Existing live emulator test extended to keep tabs open during drive/STOP. Windows/Linux full qualification pending. |
| SF-07 | Deterministic request counts recorded; matched real-browser CPU/RSS/latency and frame freshness measurements pending. |

Local Chromium is restricted by managed URL policy, including loopback. Do not claim local live-browser reproduction, physical safety, Windows qualification or completion. Independently inspect final remote CI before acceptance. Existing UI baseline and safety contracts unchanged.

First live browser run 46040042057 passed 13/13 emulator service tests but failed opening a second page in the single-page Playwright convenience context. Correct the test to use an explicit shared context; no production code change and no gate relaxation. Local two manual-lease safety cases passed against exact GitHub blobs. Replacement live qualification remains open.
