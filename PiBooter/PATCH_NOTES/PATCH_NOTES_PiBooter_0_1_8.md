# PiBooter 0_1_8 — R49 sanitized Wi-Fi operator event history

## Request / acceptance
Deliver R49 from the roadmap: a fixed-size, on-device, time-stamped history of meaningful operator actions and transitions, safely copyable from the setup UI. **Never export Wi-Fi passwords, SSIDs, IP/MAC addresses, raw NetworkManager output, paths or client data** in the new recent-event view; do not alter hotspot timing or force a scan/connection when viewing. PiBooter has no motor STOP (not applicable).

## Direct baseline and anti-rollback review
- R49 branch `update/pibooter-0_1_8-r49-recent-events` is based exactly on open draft **R46 PR #71**, `update/pibooter-0_1_7-r46-wifi-empty-state`, head `f27c8385ee0f56a162a52eb45797ce3b720139bf`. No later PiBooter R47/R48 branch exists in this selected stack; unrelated PiServer/CustomDrive R47/R48 changes are not imported.
- Inspected true `PiBooter/run_pibooter.py` entry, `pibooter/app.py`, `pibooter/state.py` (already has `RuntimeState(log_limit=...)` and a lock-protected bounded log), `onboarding_status.py` and `status_store.py`. Reviewed the latest four notes: **0_1_7 R46**, **0_1_6 R36**, **0_1_5 R35**, **0_1_4 R34**. Existing U19 hotspot security, first-client window, and network/provisioning state are preserved.
- Normal component version line: **PiBooter/0.1.7 → PiBooter/0.1.8** (existing `RequestHandler.server_version`).

## Root cause
Existing PiBooter Recent log displays private raw network and HTTP messages, including SSID, hotspot name, IP addresses and potentially exception text. These records are useful locally, but unsafe to copy into troubleshooting chats. Its bounded internal state log already prevents unlimited growth; adding a second unsanitized storage layer would increase risk and reset state unnecessarily.

## Files changed and exact behavior
1. **New** `pibooter/recent_events.py`: a pure **read-only projection** over the *newest 200* entries of the existing bounded `RuntimeState.snapshot()['logs']`, returning **at most 80** safe events. Strict phrase allowlist classifies Wi-Fi scan, Wi-Fi connection request/success/failure, saved profile removal, hotspot start/stop, setup-session start/timeout, controller start and background monitor failure. Output has only UTC timestamp, fixed `operation/category/title` and `succeeded/failed/observed`; no original message or parsed SSID/IP/path/credential is returned. Unknown/raw HTTP requests are dropped. The underlying configured fixed-size log, network and config stores remain unchanged.
2. `pibooter/app.py`: add **GET `/api/recent-events`** returning safe projection of `self.controller.state.snapshot()` (not `refresh_state` and not a new nmcli scan). Replace the old web Recent log presentation with a **collapsed sanitized event view** and Refresh/Copy buttons. Inline JavaScript uses an on-demand GET and text-only rendering (no HTML injection), clipboard API/fallback, and preserves existing status polls, network scan, POST security, setup window and Wi-Fi forms. Server version bumped **0.1.8**. No Wi-Fi network mutation or password in view.
3. **New** `tests/test_recent_events_r49.py`: **16** Python tests for log classification, sensitive names/password/IP/path suppression, timestamp bounds, fixed 80-item output, existing state 20-item bound, GET route, CSRF/origin preserved and no fake motor controls.
4. **New** `tests/test_recent_events_ui_r49.cjs`: **8** Node tests parsing Python-embedded JavaScript and checking default collapsed view, GET-only Refresh, Copy, no raw export and same-origin POST security.
5. `PiBooter/README.md`: safe operator workflow, limits and exact tests.
6. This `PiBooter/PATCH_NOTES/PATCH_NOTES_PiBooter_0_1_8.md`.

## Verification actually performed
- The **8/8 exact committed PiBooter embedded-script test callbacks passed** using a V8-compatible JS runner and fake browser/fetch/clipboard. Combined R49 views (PiBooter, PiServer and two CustomDrive UIs) passed **32/32**, including Copy/Refresh/STOP visibility in relevant components. This is **not native `node --test`** and does not substitute for actual Python HTML template rendering.
- Code inspection confirms new event export contains only allowlisted constant labels, outcome, timestamp and bounded list, with no raw HTTP log, SSID, password or exception field. HTML script braces and Python `\\n` escape for joined rows were checked and corrected.
- **16 committed Python tests not run on the exact GitHub checkout.** No PiBooker live Wi-Fi scan, hotspot setup, real browser, local Wi-Fi password validation, native Node or existing Python security suite run.
- **Direct-parent GitHub comparison completed before note creation:** 5 component-local changes (3 new, 2 modified), 0 behind R46 parent, 0 removed and 0 outside PiBooter. After adding this note, **6 files changed** (4 new, 2 modified). `network.py`, `provisioning_security.py`, `state.py`, `status_store.py`, `config/`, existing Wi-Fi POST form validation, short session, R35/R36 UI source and persisted user settings were not touched.

## Known limits and release gate
- New history is an **ephemeral projection of the already-bounded internal log**, not an external auditor or persisted ring. Unrecognized raw entries are omitted rather than guessed; entries can disappear when internal log rotates or PiBooter stops.
- PiBooter is a Wi-Fi setup service: **motor safety STOP events do not exist here**; they are tracked explicitly in PiServer and CustomDrive. This avoids fabricating motor telemetry.
- Run `cd PiBooter && python -m unittest discover -s tests -p 'test_recent_events_r49.py' -v`, then `node --test PiBooter/tests/test_recent_events_ui_r49.cjs` from the repo root; also run earlier PiBooter R34/R35/R36/R46/security tests. On actual Raspberry Pi, check failed and successful Wi-Fi connections, force rescan, active hotspot, expiry timing, phone/offline clipboard, CSRF/origin, no SSIDs/passwords/addresses leaking into copied event text, and that viewing events does not trigger an nmcli scan or extend the setup session unexpectedly.
- Draft only; do not merge without explicit user approval and release checks.
