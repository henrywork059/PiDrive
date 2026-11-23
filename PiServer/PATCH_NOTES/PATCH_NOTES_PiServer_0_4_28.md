# PiServer 0_4_28 — R49 bounded sanitized recent operator events

## Request / acceptance
Implement roadmap **R49 Recent-event debug ring buffer**: a fixed-size, on-device, operator-readable history of meaningful user actions, transitions, timestamps and outcomes, with **Emergency STOP** clearly identified. Permit copying sanitized events for troubleshooting, without unbounded growth, request secrets, filesystem paths, always-on polling, or cloud telemetry.

## Exact baseline / anti-rollback audit
- R49 branch `update/piserver-0_4_28-r49-recent-events` was created at head `143c7fb2140b5fd69020c485b51d27ba8e2b5b50` of the open **R48 draft PR #75**, `update/piserver-0_4_27-r48-readonly-preflight`. It is an additive **stacked draft**, not a replacement for a previous baseline.
- Reviewed the actual `PiServer/server.py` launcher, `piserver/app.py`, `services/control_service.py`, R47 `core/request_trace.py`, R48 `core/preflight.py`, existing Status dock template, and the latest four PiServer notes: R48 **0_4_27**, R47 **0_4_26**, R46 **0_4_25**, R45 **0_4_24**. Protect R43 adaptive polling, R35 STOP, R31 saved-vs-applied feedback, stored configs and theme preferences.
- Existing version scheme only: **0_4_27 → 0_4_28**.

## Root cause
The live service state reports current metrics and safety condition but no small, copyable outcome history distinguishing a failed Save or Emergency STOP from ordinary high-frequency control updates. Copying raw Flask request/response logs would risk tokens, credentials, model file paths and large runtime data. An unbounded list would grow with use and degrade a Pi.

## Exact files changed
1. **New** `piserver/core/recent_events.py`: component-owned thread-safe `deque(maxlen=128)` event ring. Each event contains **only** `timestamp_utc` (ISO UTC), allowlisted `operation`, `category`, constant `title` and outcome from `succeeded/failed/partial/observed`. Unknown operation/outcome is normalized, never interpolated into the view; `snapshot()` returns a copy of at most 80. Read-only API response observer uses Flask's **server-owned endpoint names**, not user-supplied request paths/messages; captures successful/rejected HTTP and body `ok:false`, including `saved:false` as partial. **Emergency STOP** and explicit safety rearm are different operation IDs.
2. `piserver/app.py`: registers non-mutating `after_request` capture for selected Camera/Motor Apply, camera preview, Model Upload/Load/Delete, recording/session actions, Config Save/Reload, STOP and rearm; one service-start event. **Excludes the high-frequency `api_control` route.** Adds **GET `/api/recent-events`** returning bounded sanitized entries and capacity. Existing R47 mutation error tracing, auth, safety, services and HTTP responses untouched. Bump `APP_VERSION`.
3. **New** `piserver/web/static/recent_events.js`: on-demand read-only GET when native details expands or Refresh is pressed, no automatic polling or POST. Renders only `textContent`; Copy uses browser clipboard with manual-selection fallback. Safe offline message, count, and no external transmission.
4. `piserver/web/templates/index.html`: adds a collapsed **Recent operator events (read-only)** inside existing Status dock immediately after R48 preflight, without changing panel names, dock order, layout defaults, STOP button, preview or modal. Versioned script reference.
5. **New** `tests/test_recent_events_r49.py`: **16** stdlib tests for fixed ring capacity/copy, UTC, safe constant titles, STOP vs rearm, HTTP 200/4xx failures, partial Save, no control-event floods, and no raw password/path/config.
6. **New** `tests/test_recent_events_ui_r49.cjs`: **8** browser VM tests for collapsed/on-demand GET, safe output, STOP visibility, Refresh, Copy and offline behavior.
7. `PiServer/README.md`: operator access, limitations and exact test commands.
8. This `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_28.md`.

## Verification actually performed
- **8/8 committed PiServer browser callbacks passed** in an isolated V8 fake DOM/fetch/clipboard harness against exact current GitHub JS and template. Across all four R49 browser views, **32/32** callbacks passed. This is not the native Node `node --test` runner.
- Inspected the actual event allowlist, fixed capacity, snapshot copy and after-response HTTP classifiers; no request bodies, model filenames, raw exception texts or full config/state copies occur in the **new event ring**. Endpoints exclude high-frequency manual drive.
- **16 Python tests committed but not run in an actual current-branch checkout**. No full Flask integration, physical Pi GPIO/motor/camera, browser screenshot or native Node test run. A real STOP-to-log confirmation is pending.
- **Direct-parent GitHub compare completed before draft:** R49 changes 7 component-local files before this note (4 new, 3 modified), 0 commits behind R48 parent, no deletions, no outside-component paths and no edits to services, config, R47 tracing, R48 preflight, theme, CSS or existing `app.js`. With this new note, 8 changed files (5 added, 3 modified).

## Known limits / required release tests
- This is an **in-memory, per-process** history. Entries expire automatically and vanish after reboot; this is not a durable audit log or a substitute for R47's failed-request correlation ID. Internal server logs remain separately governed.
- Route outcomes indicate server response success/failure, **not proof that hardware moved safely**. The safety latch, motor stop, model and config actions are never invoked by the event view. No automatic cloud telemetry.
- Run `cd PiServer && python -m unittest discover -s tests -p 'test_recent_events_r49.py' -v`, then from repo root `node --test PiServer/tests/test_recent_events_ui_r49.cjs` and existing suites. On real Pi test STOP engaged/rearm, `saved:false`, failed Apply, model upload, recording events, clipboard over non-HTTPS Pi HTTP, 60ms control responsiveness and no config reset. Recheck R48 preflight, R47 trace, R43 polling, R35 global safety and responsive widths.
- Do not merge before upstream R48/R47/R46 and explicit user authorization.
