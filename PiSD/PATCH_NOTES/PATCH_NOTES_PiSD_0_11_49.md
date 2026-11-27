# PiSD 0.11.49 — UI2 verified operator status (provisional)
 
Package baseline: 9156909b28c8cc55eb9b4f9a7ee6f5253e92ced1

## Request, cause and scope
UI2-02/03/04/05/13: the actual emulator and hardware-fallback adapters were conflated with ordinary simulation; Manual Drive's compact telemetry and AI Mode's header could retain cached values when readiness was offline, and local selection could clear the offline indication. Current main 0.11.47 includes emulator and performance work. Reviewed current launch entry point, actual web controllers, readiness projection, API and prior notes 0.11.47/46/45/44. Historical 0.11.46 note blob matches pre-emulator main 77b3fe8d (295650606921bc6d01e3da4525afabfc1ed3ebf3).

## Changes
- pisd/web/static/js/operating_readiness.js: distinguish verified Emulator, Hardware adapter, Hardware fallback, Simulation and Unconfirmed. Hardware adapter is an observation, not motor permission or movement. Contradictory emulator/physical status is unconfirmed.
- manual_drive.js and ai_mode.js: retain offline flag across local selections, explicitly recover only after confirmed status render, align visible runtime/adapter/model/camera telemetry with readiness; avoid unchanged tone/text writes where added.
- manual_drive.html, ai_mode.html and operating_readiness.css: explicit mode text and shared semantic foreground tokens using existing contrast values. No new control, arming confirmation, geometry rule or polling timer. AI status API adds requested/runtime mode alongside existing fields.
- scripts/test_operating_readiness.cjs: four additional deterministic projection cases; 36/36 real helper tests executed in V8 with a small assertion harness; full modified JS parses in V8. Exact Node/browser/Python CI pending.
- version marker and shared candidate qualification changes.

## Verification and limits
Previous UI2 Linux run 46028062905 passed all component regression jobs but failed the merged PiServer package baseline check. Emulator 46027914565 likewise passed components but failed historical note comparison; current merged main restores historical note. New explicit one-step package baseline retains current source; unchanged trainer must use an exact identical previously qualified ancestor, not skip package checks. No approved baseline changes; actual new web screenshots and visual comparison, native touch, physical Pi, latency and performance qualification remain pending. No change to motor commands, leases, STOP, GPIO, camera lifecycle, AI/model contracts, auth, saved config or data. No merge/stable promotion.

## Revision B — compact workflow navigation
- Manual Drive and AI Mode expose narrow-view navigation directly to the existing camera, recording, calibration/rate settings, model and recording-library controls as applicable. Links do not execute those controls. Desktop layouts, motor authority, STOP, capture and recording contracts, and saved presentation/config values are unchanged.
- Browser regression adds real anchor activation, single navigation interaction, elapsed time, target geometry and no-mutation checks; current layout/recording gates remain intact. New CI and candidate screenshots pending; no measured improvement claimed yet.
- Current provisional version retained; existing approved web screenshot reference untouched.


## Main reconciliation
Owner requested merging all active work. Renumber this UI2 candidate to 0.11.49 because main already contains qualified 0.11.48 emulator iframe repair (#96). Preserve the 0.11.48 note and security policy byte-for-byte. Apply only the additive AI status hunk to current app.py, retain all other runtime, config, motor and frame behavior. Combined CI and owner visual acceptance pending; no stable promotion.


## Update B checkpoint — settings request feedback loop (2026-11-28)

Separate stacked draft from exact green integration parent a4b9496b9c5d302b9a574e7e69984d8686b13b4f; do not merge into main or promote stable. Keep this existing provisional marker while the parallel 1.0.0 candidate is reconciled. Main and the integration parent have identical affected source blob a9bad7b5330fdbda30d5ff17f470768c09689517. Reviewed 0.11.49, 0.11.48, 0.11.47 and 0.11.46 notes. No physical runtime, GPIO, control command, heartbeat, camera, auth, layout, model, config schema or recorder code changed.

Cause: every relevant storage event invoked GET /api/settings; the read response wrote the full runtime cache with a fresh saved_at, causing remote storage events and repeated requests. Replace the echo with relevant, current presentation-only cache propagation. Compare JSON structurally, do not rewrite or restamp equal values, preserve other runtime keys, use the full runtime cache ahead of delayed dedicated-cache events, and coalesce presentation reads with a 3.5-second abort timeout. Reject delayed differing responses after a newer cache value. Existing page-specific explicit settings requests and mutations remain unchanged; this is not global API request throttling or cross-tab transactional backend writes.

Files: PiSD/pisd/web/static/js/panel_presentation_global.js; new PiSD/scripts/test_panel_presentation_sync.cjs and registered invocation in test_settings_feedback.cjs; PiSD_Emulator/scripts/test_frame_browser.py; this note and the settings-flood roadmap. Existing safety tests and browser STOP assertions retained.

Local verification: exact original Git blob reproduced non-settling echo at bounded cutoff of 251 GETs and 252 writes in deterministic Node three-context storage simulation. Candidate exact blob 64521544d00a932796d8b86abcb210cc46499a33: six new tests passed; initial three GETs/two writes settle; no unrelated notification echo, idempotent cache, rapid updates, stale and timeout/failure protection, and page-specific cache compatibility. Node syntax passed. Managed local Chromium blocks all navigation including localhost; no local live-browser or physical PASS. Added actual embedded/direct/editor multi-context save/readback, 60-second quiet window and virtual STOP/no-late-output checks to existing emulator browser acceptance; exact remote CI pending. Real Windows/browser, performance/CPU/RSS and physical evidence not yet obtained. No version bump or release claim.
