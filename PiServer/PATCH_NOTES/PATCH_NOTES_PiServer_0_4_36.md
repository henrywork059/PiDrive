# PiServer 0.4.36 — Batch 4 / UX75 delayed status ordering

## Request and root cause
Continue Batch 4 from 05c242f (CI 45433987366, four jobs passed). A status GET pending during a successful mutation may return an older snapshot after the mutation acknowledgement has already updated the dashboard. The old read could overwrite confirmed safety and control telemetry; a superseded error could also mark a more recent confirmed snapshot unverified.

## Files and behavior
- PiServer/piserver/web/static/app.js: advance an in-memory snapshot revision whenever updateStatusUi accepts a snapshot. Polls capture that revision when starting and discard superseded results and errors. Non-superseded success/failure, 3500ms GET timeout, single-flight cleanup and retry scheduling remain unchanged.
- PiServer/piserver/app.py: candidate version 0_4_36 only.
- PiServer/tests/test_adaptive_polling_r43.cjs: three deterministic cases executing the actual polling function with delayed promises.
- tools/check_browser_ui.py: actual Chromium route fixture holds a pre-STOP status GET, injects a synthetic successful STOP acknowledgement (never forwards the POST), then delivers the old GET; checks STOP state remains confirmed until a fresh subsequent poll at four viewport widths.
- docs/ui_regression_gate.md: scoped evidence and limitations.

## Anti-rollback
Reviewed actual launcher, current JS and API routes, regression workflow, canonical main roadmap, and four PiServer notes 0.4.35/34/33/32. Preserve STOP/rearm endpoints and confirmations, server motor logic, request timeout policy, layout/style, config keys and user data. No other component or server route behavior changes.

## Verification and limitations
Parent exact CI passed all four jobs; new exact-candidate CI pending. This is a local response-ordering guard, not global ordering across clients or a physical motor safety guarantee. Synthetic acknowledgements do not demonstrate actual actuation. Native Windows, owner golden visuals and physical hardware remain unverified. Progress remains 35/56; Batch 4 remains active.
