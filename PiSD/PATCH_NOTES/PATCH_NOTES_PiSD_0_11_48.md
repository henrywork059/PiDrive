# PiSD 0.11.48 — UI2 verified operator status (provisional)
 
Package baseline: b57f02c920cd4d65fe584b8eb4dcf9bd74e6ae71

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
