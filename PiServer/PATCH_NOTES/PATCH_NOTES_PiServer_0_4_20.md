# PiServer 0_4_20 — R31 backend-confirmed camera/motor settings

## Request and root cause
Camera and motor Apply buttons previously displayed success on a 200 JSON response without checking `ok`, `saved`, or subsequent backend readback. API routes intentionally return `saved:false` on persistence failures, but the browser ignored that flag.

## Source / anti-rollback
Built directly on **R30 PiServer draft PR #37** (`update/piserver-0_4_19-preview-freshness`). Reviewed 0_4_19, 0_4_18, 0_4_17, 0_4_16 notes; inspected actual launcher `PiServer/server.py`, `piserver/app.py` and `camera/motor/config`, `camera/motor/apply` endpoints, status, HTML and CSS. Preserves R30 camera health/preview/backoff, U28 checked E-stop, model manifests and preflight, recording storage and latency telemetry, LAN auth/CSRF, motor safety/manual watchdog, panel docking/theme, and camera/motor settings.

## Changed / added files
- `PiServer/piserver/web/static/app.js`: separate camera/motor Unsaved, Applying, Applied, Failed states, no duplicate apply, retry current inputs, protected POST response `ok && saved` and GET config readback matched to backend-accepted settings and returned config. Changes while request is in flight are not overwritten by a stale response.
- `PiServer/piserver/web/static/settings_feedback.js` (new): deterministic state and recursive value matching.
- `PiServer/piserver/web/templates/index.html` and `PiServer/piserver/web/static/styles.css`: compact status/detail/retry controls inside existing camera/motor panels.
- `PiServer/piserver/app.py`: version cache marker 0_4_20 only; camera/motor APIs and motor control unchanged.
- `PiServer/tests/test_settings_feedback.cjs` (new): deterministic tests.
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_20.md` (this note).

## Semantics
Applied means endpoint reported successful runtime application, saved=true, and independent GET config agreed with user-requested values. HTTP 200 + `saved:false` is Failed, not Applied. A new edit becomes Unsaved; browser retry runs the existing route, never bypasses operator permissions. No automatic retry of motor updates, no hardware ownership change and no persisted JSON modification in patch.

## Verification
15/15 pure-state/readback tests executed in V8 CommonJS-compatible harness, and final app.js/helper syntax parsed. GitHub diff versus PR #37 is documented in draft PR. Full Node process, Flask integration, hardware motor/camera testing and browser visual tests are not done.

## Limits
Readback proves service config matches the request, but no physical motor response or persisted-file disk roundtrip is independently tested on hardware. The existing `saved:true` API flag is authoritative for persistence; on failure the operator must resolve the underlying storage error and retry.

## Accepted-value normalization
The backend may clamp or normalize submitted values. R31 checks the backend-accepted response against independent readback, then displays effective values or an explicit normalization notice rather than treating valid clamping as a persistence failure. A rejected response or mismatched accepted-value readback still shows Failed.
