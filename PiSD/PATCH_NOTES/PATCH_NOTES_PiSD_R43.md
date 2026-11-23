# PiSD 0.11.18 — R43 hidden-tab MJPEG bandwidth, safety preserved

## Request
Address PiSD's relevant part of R43 adaptive polling and bandwidth while preserving the actual Manual Drive / AI Mode Raspberry Pi runtime and all existing safety semantics. The live R43 roadmap explicitly targets PiServer/CustomDrive status intervals; PiSD is added as a **component-local MJPEG bandwidth safeguard**, not a new backend motor or inference scheduling algorithm.

## Exact baseline / anti-rollback
- R43 branch `update/pisd-r43-adaptive-stream-throttle` starts directly from **PiSD R36 draft PR #49**, `update/pisd-r36-responsive-verification`, head `cad1a09c022075df3a16fd3a525814310455280d`. R36 stacks on R35 #45. Do not merge R43 ahead of them.
- Inspected real entry `PiSD/PiSD.py`, `pisd/app.py` status and `/video_feed` endpoints, both current active pages `pisd/web/static/js/manual_drive.js` and `ai_mode.js`, and the separate legacy `main_dashboard.js` bench reference. Reviewed latest notes **R36 (0.11.17)**, previous three **R35 (0.11.16)**, **R32 (0.11.15)** and **R31 (0.11.14)** plus U28 motor-safety inheritance. Preserve latest accepted structures/config/recording paths and version 0.11.x.
- Preserve R35 global Space STOP and native keyboard input, R36 responsive layouts, R32 readiness/status strip, R31 Save/Retry, existing camera settings, recording process, AI/manual correction, U28 latched safety rearm, server motor watchdog and mode-specific update rates. No changes to backend services or persisted configuration.

## Root cause
The browser used long-lived `/video_feed` MJPEG `img.src` requests that could remain connected when tab was hidden. Manual Drive already paused its preview FPS status timer and sent a fail-safe STOP on hide; AI Mode already stopped manual corrections/assist/full manual and issued an AI stop beacon; however neither explicitly closed the MJPEG response. Hiding the page could continue to receive JPEG bytes despite no visible operator. The legacy dashboard likewise kept its MJPEG URL until camera stop.

## Files changed / exact behavior
1. `PiSD/pisd/web/static/js/manual_drive.js`: when hidden, first run existing FPS poll stop and `sendFailSafeStop('visibility-hidden')`, then release the browser MJPEG connection by assigning the existing idle-preview placeholder without changing `currentPreviewMode='live'`. On return, only if live/snapshot mode remains chosen, restore the same `/video_feed` source for live and refresh preview FPS/readiness immediately. Hidden user click on Start Live no longer starts a visible MJPEG connection. Space/STOP keyboard, arm checkbox, speed slider, physical motor and recording services unchanged.
2. `PiSD/pisd/web/static/js/ai_mode.js`: when hidden, keep existing `resetManualCorrection`, `stopFullManualDrive`, `stopAssistDrive` and `/api/ai/stop` best-effort beacon *before* releasing MJPEG `img.src`. On visible return, restart `/video_feed` only if the displayed preview mode was previously live and request immediate read-only operating readiness. `setPreview('live')` also avoids opening a stream while already hidden. Never restart AI drive automatically: this is only a camera viewer reconnect.
3. `PiSD/pisd/web/static/js/main_dashboard.js`: legacy bench dashboard tracks whether live preview was explicitly requested. Disconnect MJPEG on hidden, reattach only if preview was requested on return, clear intent after camera Stop. No new periodic status poll.
4. `PiSD/pisd/__init__.py`: version **0.11.17 → 0.11.18** so existing cache-busted assets use the new client behavior.
5. `PiSD/scripts/test_adaptive_stream_r43.cjs` **new** — 6 Node source/safety assertions for hidden streaming, return, STOP ordering, AI modes and existing backend `timestamp_utc`.
6. `PiSD/README.md`: bandwidth behavior, expected before/after streaming profile and hardware test gate.
7. `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_R43.md` — this note.

## Verification actually performed
- JavaScript syntax parser against all three **exact live GitHub modified files**: **3/3 passed**.
- Combined **22/22 live-source static safety/anti-rollback checks** across PiServer/CustomDrive/PiSD passed, including original Manual/AI hide STOP paths and original existing status server timestamps.
- Standalone `test_adaptive_stream_r43.cjs` contains **6 tests**, but is **committed, not executed end-to-end** in a locally mounted GitHub checkout. Physical Pi HTTP/MJPEG stream termination, camera preview on tab return, motor STOP/AI stop, recording continuity, phone browser tab behavior and real bandwidth counters have **not** been tested.
- Review branch changes against direct parent R36 for no deletions, no files outside PiSD, and no interference with R35/R36/earlier accepted styles/config/control services before draft PR.

## Before/after bandwidth profile (expected design, not a measured benchmark)
- **Before**: a live page could keep one continuous MJPEG HTTP response streaming JPEG frame bodies even when the tab was hidden. Depending on camera FPS, quality, image size and browser behavior, hidden bytes/sec could remain near visible bytes/sec.
- **After**: the viewer disconnects the MJPEG HTTP response while hidden, aiming for **zero MJPEG payload bytes/sec during the hidden interval**. It reopens only on visible return if live preview was selected. This is bandwidth reduction, not a per-minute request count: a continuous MJPEG stream is usually *one long-lived GET*, so dividing 60 seconds by a timer interval would be meaningless.
- The active preview rate, server camera capture rate, inference update frequency, video/recording FPS and motor-control frequency are unchanged. Server `/api/status` already exposes `timestamp_utc` and camera FPS stats expose frame age and sequence, so R43 does not add a redundant timestamp or claim a stale cached preview is live.

## Known limits / next steps
- Closing an `img.src` is a browser cancellation hint; actual network close, buffering and camera generator response handling depend on browser and Flask/server behavior, which require on-device packet/HTTP tracing. Recording is supposed to stay running on the server even when browser MJPEG display is hidden; test this explicitly.
- Image load/error callbacks may still fire around visibility transitions; monitor preview state on return and verify server freshness rather than trusting a placeholder image load. No motor command is issued to reconnect the viewer.
- Run `node --test PiSD/scripts/test_adaptive_stream_r43.cjs`, full PiSD tests and physical Raspberry Pi camera motor safety checks. Collect 60-second live/hidden/resumed transfer bytes from DevTools or server logs; test Manual/AI/legacy pages, Space STOP, AI safety stop, stale/recovered camera, recording continuity, R35 accessibility and R36 phone layout. Do not merge without explicit approval.
