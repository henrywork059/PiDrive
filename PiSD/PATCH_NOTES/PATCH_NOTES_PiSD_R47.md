# PiSD 0.11.20 — R47 safe mutation correlation and error-history redaction

## Request
Complete roadmap R47 on the real Raspberry Pi **PiSD** Flask runtime: correlate failed Apply/Start/Drive/STOP and other API mutations with one bounded server log entry and an ID visible in expandable operator details. Sanitize existing `/api/errors` and status exports, never add secrets or paths to new logs, and preserve motor/AI safety and the existing PiSD error-code registry.

## Live baseline / anti-rollback
- Direct parent: draft/open/unmerged **R46 PR #67**, `update/pisd-r46-terminology-empty-states` at `0976e36cef05a00430fa825e66f807a3b1c5b47d`; R47 branch `update/pisd-r47-request-tracing` is layered on that commit, **not main/old ZIP**.
- Verified real `PiSD/PiSD.py` entry, `pisd/app.py`, `pisd/core/errors.py`, active `manual_drive.js` and `ai_mode.js`; read latest R46 **0.11.19**, prior three R43 **0.11.18**, R36 **0.11.17**, R35 **0.11.16** notes. Preserve R32 readiness, R31 settings feedback, R35 global Space STOP, R36 responsive camera and R43 hidden-MJPEG stop/reconnect.
- Version line: `pisd/__init__.py` **0.11.19 → 0.11.20** only. No runtime setting/config schema migration and no change to motors, AI inference, camera capture, output guard, recording storage or endpoints.

## Root cause
Existing `ErrorReporter` records can include raw absolute filenames, exception messages or credential values in `as_dict()` exported via `/api/errors` and `/api/status`. Failed mutations return PiSD-coded JSON but no common server-generated reference to locate the same failed action in the application log. Manual Drive's debug console previously stringified entire failed API responses, including potential runtime settings, and could show rejected camera Start/STOP/Recording as successful in the same screen.

## Files changed / exact behavior
1. **New** `pisd/core/request_trace.py`: failure-only Flask `after_request` tracing for POST/PUT/PATCH/DELETE `/api/`. A failure is HTTP >=400 or JSON `ok:false` **or** `saved:false`. Add server-generated random 16-hex `correlation_id`, safe `operation` from Flask endpoint, and `X-Correlation-ID`; retain original code, original HTTP status (including 200 for legacy `ok:false`), and existing PiSD `code`, `error`, `settings` and `safety` fields. Unexpected HTML mutation errors are converted to safe JSON without changing HTTP status. Emit **exactly one new warning line per failure** using only ID, operation, status, validated error code (never request body, user headers, exception repr, or full response). Helpers redact credential tokens/URLs, explicit filenames/absolute paths and traceback keys in diagnostics, cap depth, size and string length.
2. `pisd/app.py`: install hook in the actual Flask app factory **without modifying the existing static cache after-request hook, service init, PiSD code registry or safety guards**.
3. `pisd/core/errors.py`: `ErrorReport.as_dict()` sanitizes messages/context on export, including for status and `/api/errors`; even with `include_traceback=True`, return a redaction marker rather than revealing stack lines. `ErrorReporter.status_fields` also sanitizes last error; `report_payload` sanitizes reported diagnostic messages. In-memory reports remain intact internally; only exported diagnostic views are redacted. Existing `code`, `timestamp_utc`, `severity`, `component` remain.
4. `pisd/web/static/js/manual_drive.js`: existing action console now outputs a bounded failure record (`ok`, code, ID, operation, HTTP status) instead of serializing raw failed payloads; a collapsible **Error details** next to existing short-status text shows only validated server metadata. Prevent failed manual commands, STOP, camera Start and Record/Stop Recording from being labelled as confirmed success; the existing fail-safe STOP attempt and motor service are unchanged.
5. `pisd/web/static/js/ai_mode.js`: failed-API `Error` holds sanitized minimal trace payload; existing logger shows short actionable error and a collapsible metadata-only `Error details`. The existing AI prediction, motor and manual correction cycles and R43 read-only polling are untouched. PiSD `/api/errors` export remains a read-only endpoint and now returns sanitized history.
6. `pisd/__init__.py`: version **0.11.20** for existing cache-busting.
7. **New** `scripts/test_request_trace_r47.py`: 15 hardware-free stdlib Python tests for actual after_request hook using a fake Flask response contract.
8. **New** `scripts/test_error_export_r47.py`: 5 stdlib tests for actual `ErrorReporter` history, traceback exclusion, status fields and bounded history.
9. **New** `scripts/test_request_trace_ui_r47.cjs`: 9 Node browser source/safety/error-history tests.
10. `README.md`: ID lookup, privacy, tests, physical release gate.
11. `PATCH_NOTES/PATCH_NOTES_PiSD_R47.md`: this note.

## Verification actually performed
- Modified PiSD Manual and AI JS both passed live-source V8 syntax parse; five active R47 browser files across three components parsed **5/5**.
- The **9/9 exact committed PiSD Node callbacks passed** through a V8 compatibility harness using current live GitHub source; across the entire R47 UI group **28/28** committed callbacks passed. This is **not native `node --test`** or a real browser.
- Python diagnostic-redaction expression was compiled with real Python `re` and exercised on quoted relative, Windows and Linux paths. The initial quoting error in the new source literal was corrected before final checks.
- **20 committed Python tests** (15 request-hook + 5 error-export) are **not executed** on a checkout of the latest branch; Flask is not installed locally. There were **no actual Raspberry Pi motor/camera/AI/recording or full Python test runs**.
- Direct GitHub parent comparison/rollback audit must be performed and recorded in PR before merging; no test suite is claimed as hardware-tested.

## Known limits / release gate
- New failure ID is generated only for failed JSON/API mutations, not read-only GET, successful POST or browser network failures where server has never received the request. Correlation IDs from client headers are ignored.
- The `ErrorReporter` export is now redacted but internal service state/history and legitimate successful config/model API payloads remain unchanged. Broader sensitivity review of all state/config exports is a separate security task; do not claim all old API fields are safe.
- Run `python -m unittest discover -s PiSD/scripts -p 'test_request_trace_r47.py' -v`, `python -m unittest discover -s PiSD/scripts -p 'test_error_export_r47.py' -v`, `node --test PiSD/scripts/test_request_trace_ui_r47.cjs`, then full PiSD test suites. On Raspberry Pi: failed camera Start, STOP, invalid motor settings, rejected AI/recording, simulated vs real motor and safety rearm; verify HTTP 200/400/409/500+error-code compatibility, missing camera, session recording and hidden-tab network bytes. Verify ID in UI matches one bounded log line, and that error history omits passwords/paths.
- **Draft only. No merge authorized** without upstream R46/R43/R36/R35 acceptance.
