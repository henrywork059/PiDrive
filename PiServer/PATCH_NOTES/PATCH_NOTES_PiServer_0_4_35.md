# PiServer 0.4.35 — Batch 4 / UX75 bounded read-only waits

## Request and root cause
Continue from latest green 7fba71c PiServer 0.4.34, CI 45431856457 (four jobs passed). Previous disconnected tests covered immediate HTTP 503 replies; the live fetchJson GET calls had no timeout. An indefinitely pending read blocked sequential init; an indefinitely pending /api/status held the existing state.statusInFlight guard, meaning status retries could be suppressed forever, leaving operator telemetry stale and no recovery.

## Changed files and exact behavior
- PiServer/piserver/web/static/app.js: add READ_ONLY_TIMEOUT_MS = 3500, AbortController and a finally-cleared timer only for GET calls without a caller-supplied signal. Timed-out reads reject clearly, allowing existing status-failure UI, automatic retry and E-STOP uncertainty guard to run. HTTP error trace handling preserved. POST mutations (STOP/rearm, motor, camera, config, model, recording) deliberately do not acquire the new request timer because network cancellation does not mean the server discarded a command.
- PiServer/piserver/app.py: advance existing candidate 0_4_34 to 0_4_35. No Python route/runtime changes.
- tools/check_browser_ui.py: actual Chromium+Flask simulation intentionally leaves cold-start model GET and later status GET pending, then verifies a timeout is reported, polling single-flight lock releases and next poll is scheduled, critical telemetry is unverified, STOP click requests engagement rather than rearm, and subsequent successful response restores verified status at 390/768/1024/1440. All mutation requests are intercepted (503), no physical actuation.
- docs/ui_regression_gate.md: R35/UX75 limits, test design and evidence.

## Anti-rollback
Inspected real PiServer/server.py, current JS, status polling, entire route simulation and latest plus previous three PiServer patch notes 0.4.34/33/32/31. Existing 0.4.34 unverified-state UI, named layout keys, E-STOP API/authorization, manual 60ms command tick, backend hardware watchdog, saved config, recording/model data and other components unchanged. Existing frame.jpg request has its own independent 3000ms deadline and was not changed.

## Tests and known limits
Source and regression scenario reviewed; exact new CI result must be checked before claiming pass. Timeout is client-side only, not proof of stopped motors nor of server cancellation; a client abort of GET does not affect safety-critical POST completion. An external signal remains caller-owned and is not overridden. Browser simulation is not a slow cellular network/hardware test, native Windows, a golden screenshot, or merge/deployment approval. Progress counts stay 35/56; remaining Batch 4 R35/R36/R50/UX75 gates open.
