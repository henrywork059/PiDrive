# PiServer 0_4_26 — R47 safe failed-mutation tracing

## Request and scope
Implement roadmap **R47 — Request tracing and errors** for the actual PiServer Flask runtime: failed API mutations must return a server-issued correlation ID and a stable operation name, emit one bounded matching log entry, and show a short operator-facing error with expandable **Error details**. Exported diagnostic fragments must not contain credentials or sensitive absolute/explicit file paths. Preserve live control, camera/motor safety, access control and R31 saved-vs-applied semantics.

## Baseline and anti-rollback
- Direct parent: open, unmerged draft **R46 PR #66**, `update/piserver-0_4_25-r46-empty-states`, head `73ee1088d3f37e5cffd4112d37a6432e98566402`. New R47 branch `update/piserver-0_4_26-r47-request-tracing` is stacked onto exactly that head; never merge before dependencies.
- Inspected real `PiServer/server.py` entry, current `piserver/app.py`, `core/access_control.py`, browser `web/static/app.js`, live error responses and settings readback, and latest notes R46 **0_4_25**, R45 **0_4_24**, R43 **0_4_23**, R36 **0_4_22**. R35 focus/STOP and R31 config confirmation remain protected.
- PiServer retains 0_4_x patch line; `APP_VERSION 0_4_25 → 0_4_26`. No config reset, folder movement or launch change.

## Root cause
Existing failed mutations returned JSON (`ok:false`, HTTP 400/403/500), and some partially failed to persist (`saved:false` with HTTP 200), but lacked a request-to-log correlation key. Generic UI errors could expose raw exception text and required guessing the failed operation; using request payloads or full response JSON for diagnostic logs would risk disclosing tokens, absolute paths, and runtime settings.

## Files changed and exact behavior
1. **New** `piserver/core/request_trace.py`: `install_mutation_trace(app)` installs a *failure-only* Flask `after_request` hook for POST/PUT/PATCH/DELETE under `/api/`. Failure means HTTP status >=400 **or** JSON `ok:false` **or** JSON `saved:false`. It creates a fresh cryptographic 16-hex `correlation_id`, sanitized server-owned `operation` from `request.endpoint`, and `X-Correlation-ID`; appends the two JSON fields only on failures, preserving other JSON keys and **original HTTP status including legacy HTTP 200 errors**. Unexpected HTML 500 mutation responses become safe JSON while retaining 500 status. One `app.logger.warning` line reports only ID, operation, HTTP status and a validated code. No request bodies, headers, passwords, bearer tokens, full URL/path, config objects, or exception reprs are logged. `safe_diagnostic_text` and `safe_diagnostic` redact URLs, bearer/secret assignments, explicit path assignments, Linux/Windows absolute paths, sensitive map keys/tracebacks, and cap string lengths and nesting.
2. `piserver/app.py`: call trace-hook installer **after** existing access-control installer so 401/403/CSRF rejections are traceable without bypassing security; advance only `APP_VERSION`.
3. `piserver/web/static/app.js`: distinguish failed HTTP responses, `ok:false`/HTTP 200 and mutation-only `saved:false`, never misclassifying GET; wrap an error with short action-specific Camera/Motor Apply guidance. Render safe, collapsible `<details>` **inside the existing** Camera/Motor error banners, containing only validated ID, endpoint, HTTP status and optional error code. Retain login redirect, R31 Apply sequencing and successful backend readback; **never** show request body, backend exception or filesystem path in new trace UI.
4. **New** `tests/test_request_trace_r47.py`: 15 hardware-free stdlib tests using a minimal mocked Flask `after_request` contract. Verify 401/403, JSON/HTML errors, 200 + ok:false/saved:false, GET/POST separation, code/ID bounds, one logger invocation and redaction without touching motor/camera.
5. **New** `tests/test_request_trace_ui_r47.cjs`: 9 Node tests extracting actual browser helpers and checking short text, expandable safe details, malicious IDs, semantic operation, unchanged auth/STOP and R31/R43 source safeguards.
6. `README.md`: operator lookup, exact test commands and privacy limits.
7. `PATCH_NOTES/PATCH_NOTES_PiServer_0_4_26.md`: this note.

## Verification actually performed
- Parsed **all 5 changed browser scripts across the R47 series** using V8: **5/5 passed**.
- Ran **9/9 actual committed PiServer browser test callbacks** against exact GitHub source in an isolated V8 compatibility harness, plus executable DOM/helper checks. Across all three R47 UI components **28/28** callbacks passed. This is **not native `node --test`**.
- Validated the Python path-redaction regex with real Python `re` against quoted relative, Linux and Windows path examples; the initial malformed expression was corrected before final verification. **The full 15 committed Python test cases were not run** in a GitHub checkout. Flask is absent in the local environment; full backend integration, real auth, network captures, camera/motor tests and actual browser screenshots have not been performed.
- **Direct-parent GitHub comparison completed:** PiServer R47 is **11 commits ahead, 0 behind** R46 PR #66, with **7 changed files (4 new, 3 modified), no deletions and no files outside PiServer**. Access-control logic, motor/camera services, responsive CSS/theme, R43 preview and R45 style overrides remain untouched.

## Known limits and next steps
- Existing normal `state` or successful config/model payloads are not rewritten. R47 sanitizes **new trace diagnostics and failed mutation `message`/`error` fields**, not every pre-existing data field emitted by all APIs. No credential values are accepted from `X-Correlation-ID` headers.
- Logs intentionally exclude raw exception details; an ID links UI to one bounded failure record, not a full exported exception stack. Avoid repurposing the log line for request body dumping.
- Run `python -m unittest discover -s PiServer/tests -p 'test_request_trace_r47.py' -v` and `node --test PiServer/tests/test_request_trace_ui_r47.cjs`, then full PiServer tests. Test a 401/403 from token/CSRF gate, failed camera/motor Apply, 200/saved:false, HTTP 500, login recovery, R31 persisted settings, R43 FPS polling and physical STOP. Verify exactly matching ID in one log line. No PR merge authorized.
