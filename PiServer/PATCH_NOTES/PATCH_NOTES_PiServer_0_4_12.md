# PATCH NOTES — PiServer_0_4_12

## Request summary
Implement roadmap F3: protect PiServer LAN access, including motion, camera,
recording, model and settings endpoints; retain the 0_4_11 safety watchdog.

## Cause / threat model
Prior PiServer served unauthenticated remote HTTP requests on 0.0.0.0:5000.
Any LAN client could issue motor commands, disarm E-stop, download recordings,
or view camera frames without any authorization.

## Baseline and anti-rollback
- Stable baseline: PiServer_0_4_0; new patch in the 0_4_x line.
- **Stacked on draft PiServer_0_4_11 PR #9**, not the older main source.
- Reviewed 0_4_11 note and prior 0_4_10, 0_4_9, 0_4_8, 0_4_7 history.
- Preserves AWB-off defaults, UI layout namespace, snapshot/download behavior,
  camera settings, the 0_4_11 numeric-input stop and manual-command watchdog.

## Files changed
- PiServer/server.py
- PiServer/piserver/core/access_control.py (new)
- PiServer/piserver/app.py
- PiServer/piserver/web/static/app.js
- PiServer/piserver/web/templates/login.html (new)
- PiServer/README.md
- PiServer/tests/test_access_control.py (new)
- PiServer/tests/test_access_api.py (new)
- PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_12.md (new)

## Behavior changes
- Without a configured token, the runtime binds only to localhost and rejects
  non-loopback requests at the Flask layer. Explicit remote binding without a
  token fails at startup; no changes to persistent runtime/config files.
- With PISERVER_ACCESS_TOKEN (32+ chars), LAN binding is available, and all
  HTTP routes require bearer auth or an authenticated browser session.
- Browser sign-in is POST-only; the token never appears in the URL or browser
  storage. Sessions use HTTP-only SameSite=Strict cookies and random CSRF
  tokens for mutating requests; crossorigin session POSTs are rejected.
- Bearer auth is supported for non-browser API clients without cookie CSRF.
- Private request responses set no-store for the login and auth endpoints,
  deny framing, disable MIME sniffing, and constrain referrers.
- The existing fetchJson wrapper adds the CSRF header to browser POSTs,
  including model upload, while preserving existing UI controls/layout.
- APP_VERSION advances to 0_4_12 for browser asset cache busting.

## Verification actually performed
- Local compileall and unittest discovery executed on the layered PiServer tree.
- Node JS syntax check executed on app.js.
- Flask test-client integration scenarios are included but skipped if Flask
  is unavailable in the local environment; these must run before merging.
- Real Pi hardware, TLS reverse proxy, and remote browser login not tested.

## Known limits
- HTTP over an untrusted LAN is not confidential: prefer HTTPS/VPN.
- Login sessions are in-memory-secret signed and reset after restart unless
  PISERVER_SESSION_SECRET is provided. Never commit tokens or session secrets.
- This change provides authentication/CSRF, not request rate limiting or
  independent electrical motor emergency cutoff.
- Server branch depends on merging PR #9 first; review this PR as stacked.
