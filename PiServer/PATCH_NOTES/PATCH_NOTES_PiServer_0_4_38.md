# PiServer 0.4.38 — Batch 4 / UX75 recording acknowledgement recovery

## Request and root cause
Continue from 6b782f7 (CI 45515079463, four jobs passed). Recording toggle used one catch for POST and follow-up folder GET; a rejected folder read reverted an already acknowledged recording indicator and prevented immediate status poll. Snapshot capture likewise propagated the optional read failure as though the command failed.

## Changed files and behavior
- PiServer/piserver/web/static/app.js: separate POST rejection from acknowledged recording state, catch optional folder read independently, retain status poll and show partial-success/retry guidance. Snapshot success remains success if folder GET fails; pending cleanup and rejected POST behavior preserved.
- PiServer/piserver/web/templates/index.html: existing folder banner becomes a polite status region.
- PiServer/piserver/app.py: candidate version only.
- PiServer/tests/test_recording_feedback_ux75.cjs: six deterministic cases executing actual functions; registered in .github/workflows/regression.yml.
- tools/check_browser_ui.py: actual Manual workspace synthetic start/stop/snapshot acknowledgements plus failed folder reads and rejected POST at four widths; no mutation forwarded.
- docs/ui_regression_gate.md: scoped evidence and limitations.

## Anti-rollback
Reviewed current launcher, API contract, actual JS/browser tests, canonical roadmap and latest notes 0.4.37/36/35/34. Retains model refresh selection/revision, status revision, timeout, STOP/rearm, recording API/storage, configuration and layout. No server behavior changes.

## Verification and limits
Parent full CI green; exact new CI pending. Acknowledgement is not hardware proof; POST transport failure remains the existing rollback presentation, not proof of command cancellation. Native Windows, physical Pi, owner visual acceptance and wider UX75/R35/R36/R50 remain open. Counts stay 35/56.
