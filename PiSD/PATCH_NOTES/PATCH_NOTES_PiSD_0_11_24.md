# PiSD 0.11.24 — F2 manual command watchdog

## Request and cause
Manual/AI-assist direct motor commands could remain active after a lost STOP packet. Add a server-side monotonic lease at the actual motor service, preserving accepted drag and incremental keyboard behavior while a connected page is active.

## Changed behavior/files
- pisd/services/motor_service.py: one lazy condition-based watchdog per motor service, 0.85 s manual/assist lease; private per-command token; renewal never reapplies a command; expire/stop/owner change invalidate token. Other timed tuning and AI control paths are not leased by this manual-only policy. Failed manual adapter output requests stop. Status exposes timeout/active state without token.
- pisd/app.py, core/errors.py: return current lease only to originating command response; POST /api/control/heartbeat renews existing token or returns 409; manifest updated; existing safety acknowledgement and stop paths retained.
- web/static/js/manual_lease.js, manual_drive.js, ai_mode.js and corresponding templates: 250 ms renewal without replay; cancel on STOP, focus loss/hidden page and failed renewal; ignore late responses after cancellation. Manual page logs omit private lease field. Dashboard click is now a bounded one-shot pulse.
- scripts/test_manual_lease_f2.py and .cjs: fake clock, real timer simulation, stop/owner invalidation, HTTP heartbeat, JS renewal and cancellation tests. CI matrix expanded.
- pisd/__init__.py: 0.11.23 -> 0.11.24; README documents compatibility.

## Verification and limits
Direct parent ea60df35849856a6d53c1c6f2148617a70f86595, previous 0.11.23 and 0.11.22/R48/R47 notes reviewed. No persisted defaults/settings changes. New tests require exact-branch CI. A delayed original command is distinct from renewal; authorization and robust cross-client command sequencing remain F3/follow-up work. Watchdog is in-process and cannot guarantee GPIO stop during blocked driver/OS failure. No physical testing. Preserve the last green candidate and keep draft.
