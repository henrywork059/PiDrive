# PATCH NOTES — PiServer_0_4_11

## Request summary
Begin implementing the PiDrive engineering roadmap with a first, independently reviewable PiServer safety and control-integrity patch. Implements the PiServer portion of **F1**, **F2**, and **U13**.

## Baseline and anti-rollback
- Stable baseline: `PiServer_0_4_0`.
- Latest verified active GitHub version before this patch: `0_4_10`.
- Compared current code and previous four patch notes: `0_4_7`, `0_4_8`, `0_4_9`, `0_4_10`.
- Preserve accepted snapshot freshness, AWB-off camera default, camera diagnostics, motor direction settings, UI layout keys, runtime JSON schema, and saved configuration values.
- Version marker updated to `0_4_11`; no new version scheme.

## Root causes
- `ControlService._parse_float` accepted non-finite numbers and `_clamp` could turn NaN into `+1`.
- Manual state was reused on every control-loop tick without a finite command lease.
- `/api/control` applied manual inputs and runtime parameters before validating the requested algorithm.
- E-stop and exception paths applied steering bias after deciding that control output should be zero, potentially commanding unintended steering.
- The browser sent manual controls only while they were changing, not when an operator held a fixed command.

## Files changed
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/tests/test_control_service.py`
- `PiServer/tests/test_api_control.py` (new)
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_11.md` (new)

## Exact behavior changes
1. The control API now validates all supplied numeric values and requested algorithms before mutating runtime state. Unknown algorithms return HTTP 400 without partial mutations.
2. Invalid numeric motor/runtime inputs (including NaN and infinity) return HTTP 400 and **latch emergency stop**, zero manual outputs, and invoke motor stop. Recovery requires explicitly clearing the stop. Finite values continue to be clamped to existing limits.
3. A manual-command lease expires after **0.85 seconds** without a fresh steering/throttle packet, zeroing manual state and motor outputs. The server remains stopped without further packets and exposes `manual_command_age_s`, `manual_command_timeout_s`, and `manual_command_timed_out` in control snapshots. The lease is ephemeral, not persisted to runtime JSON.
4. The browser sends held manual-command heartbeats at most every 250 ms and attempts a zero command when the tab becomes hidden. The server watchdog does not depend on a browser STOP request arriving.
5. E-stop activation **and release** clear the manual lease and setpoints; the last manual command is not replayed. Steering bias is bypassed on E-stop, timeout, algorithm error, and zero setpoint. A motor update failure also engages e-stop.
6. The UI status explicitly reports expired manual commands. `APP_VERSION` is `0_4_11` for cache-busting.

## Verification actually performed
- Local unit suite: `python -m unittest discover -s tests -q` → **44 tests, 43 passed, 1 skipped** (Flask package is unavailable in local validation environment; new API test is automatically skipped).
- `node --check piserver/web/static/app.js` → passed.
- `python -m compileall -q piserver tests` → passed.
- Static comparison of original PiServer files against active GitHub blobs before patch and inspection of the four recent patch notes.

## Known limits and next steps
- **NOT hardware tested.** Verify watchdog latency, emergency-stop behavior, and steering/reverse operation with the wheels raised on the actual Raspberry Pi before deployment.
- Flask endpoint integration test still needs to run in an environment with Flask installed.
- F3 authorization for exposed LAN motor endpoints is **not** implemented in this patch; network access should remain isolated/trusted until a separate security update is tested.
- PiSD and CustomDrive motor arbitration/timeouts are unchanged; they require their own component-specific patches.
- Client requests can still arrive out of order under network delay; an explicit control sequence/generation protocol is a subsequent improvement.
