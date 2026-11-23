# PiServer 0_4_19 — R30 camera preview freshness

## Request / root cause
The browser could repeatedly display a cached JPEG as if live, and the previous preview loop silently retained the last image on a failed frame request. A backend can publish placeholders while `preview_live=false`. Fix user-visible freshness without altering camera ownership or motor safety.

## Baseline and anti-rollback
Built directly on unmerged **PR #33**, branch `update/piserver-0_4_18-safety-contract` (commit `4dba2c51ed9e696af5d02227055ba6c7905ea33f`), not main or an uploaded ZIP. Reviewed 0_4_18, 0_4_17, 0_4_16, 0_4_15 notes. Preserves U28 confirmed E-stop rearm; U27 model manifest/preflight; U26 protected recording/storage; U23 latency metrics; U14 exclusive hardware ownership; U12 dynamic model checks; F3 LAN protection/CSRF; manual deadman, camera controls, layouts, styles, overlays and persistent settings.

## Changed/new files
- `PiServer/piserver/app.py`: additive `X-Preview-Seq` (atomic JPEG sequence) and `X-Preview-Live` (camera backend validity) response headers on the existing protected, no-store JPEG endpoint; version 0_4_19.
- `PiServer/piserver/web/static/app.js`: monotonic client age; decode before swapping the displayed JPEG; retain last successful frame; bounded retry backoff; status refresh.
- `PiServer/piserver/web/static/preview_freshness.js` (new): independent deterministic state machine.
- `PiServer/piserver/web/templates/index.html`: live-status indicator and additive script.
- `PiServer/piserver/web/static/styles.css`: noninteractive overlay and muted stale-frame appearance.
- `PiServer/tests/test_preview_freshness.cjs` (new): deterministic fresh/delayed/disconnected/recovered/paused/failure/sequence/backoff tests.
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_19.md` (this file).

## Exact behavior
Fresh = last unique decoded live JPEG younger than 1.5 s; Delayed = 1.5–6 s old or a recent failed request; Disconnected = >=6 s old, no successful frame, or backend reports offline. Display frame age in seconds using browser `performance.now()` (not wall-clock time). Repeated cached JPEG sequences do not update age; invalid/empty/decode-failed JPEGs cannot claim Live. Last good JPEG stays visible with `STALE` state and visual dimming. Sequential failures retry from 250 ms to 4 s with deterministic exponential backoff; a fresh unique JPEG resets retry delay and restores Live without user interaction. Hidden tabs retain the existing preview pause semantics and manual STOP-on-hide behavior. The legacy JPEG response body, route, access controls, cache headers and other camera APIs remain unchanged.
- 3-second browser request timeout and missing/invalid JPEG sequence header rejection; neither hung network calls nor incomplete metadata can keep the preview marked Live.

## Verification actually performed
- Executed the **exact 14 deterministic state tests** from `PiServer/tests/test_preview_freshness.cjs` in the connector's V8 runtime with a small CommonJS/assert adapter: **14/14 passed** (fresh, delayed, disconnected, recovery, repeated/invalid sequence, offline backend, failure, pause, bounded backoff).
- Parsed the complete final `piserver/web/static/app.js` and `preview_freshness.js` with V8 JavaScript compilation: passed.
- GitHub compare against immediate parent PR #33: all changes confined to PiServer; 7 paths (4 modified, 3 added), no deletions or unexpected restores; the E-stop confirmation and manual stop-on-hide hooks remain.
- Reviewed the actual `PiServer/server.py` launcher and the existing `/api/camera/frame.jpg`, `/api/camera/preview_state`, `/api/status` endpoints. No motor/controller or config path changed.
- **Not run:** `node tests/test_preview_freshness.cjs` as a Node process, Python compilation or Flask end-to-end tests against this GitHub branch, browser image-decode integration, Raspberry Pi camera or motor tests. V8 checks are not a substitute for device testing.

## Limits
Sequence measures *published preview JPEG changes*, not physical sensor exposure time; backend Live validity is a separate signal. The server may hold a JPEG published just before a camera fault until it reports disconnected. The browser preserves the last decoded image only; no historical frames are written. Raspberry Pi camera, real reconnection and physical motor safety are unverified.
