# PiSD 0.11.25 — F3 LAN operator access

## Request and root cause
Batch 1 F3: the real PiSD launcher allowed 0.0.0.0 with no authentication, including camera, motor, settings and recording routes. The prior F2 watchdog limits abandoned manual output but is not authorization.

## Changes
- PiSD.py and pisd/app.py: validate access configuration before hardware construction; refuse non-loopback launcher binding without a token.
- pisd/core/access_control.py: centralized request gate for all routes; local-only peer and Host checks; explicit LAN bearer credentials or signed browser session; same-origin browser mutation proof and strict cookie, including authorized STOP and sendBeacon. No secrets in settings. New API error codes.
- web/templates/login.html and front_page.html: accessible login; front page STOP-and-sign-out uses existing STOP operation and does not clear session if STOP fails.
- core/request_trace.py: redact manual lease identifiers in diagnostic objects.
- scripts/test_access_control_f3.py and regression workflow: real Flask simulation tests for bind, unauthorized service calls, cross-origin, bearer, login/session, heartbeat, degraded STOP, failed sign-out and successful sign-out.
- pisd/__init__.py: 0.11.24 -> 0.11.25; README documents migration, systemd environment, HTTP risks and client compatibility.

## Verification and anti-rollback
Direct parent d7b1ef2176f2054b00a62fac51c23395e8d3cc53 passed all four CI jobs (45356933493). Reviewed latest 0.11.24 plus 0.11.23/22/R48 notes, actual launcher/app, global STOP and PiServer access policy. Existing UI, command lease, camera latch, recording/model paths and runtime settings remain. New CI required on this exact commit. No real Pi testing. LAN startup now intentionally requires a strong token; existing services must configure it before deploying. No encryption, per-user roles, physical stop or cross-client sequencing guarantee; use isolated network or HTTPS and verify physical hardware separately.
