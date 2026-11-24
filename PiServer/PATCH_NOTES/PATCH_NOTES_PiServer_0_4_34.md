# PiServer 0.4.34 — Batch 4 / UX75 disconnected initialization and E-STOP uncertainty

## Request and observed root cause
Continue Batch 4 from the exact green b379138 (CI 45426094777, 4/4). Actual piserver/web/static/app.js init awaited model/session/camera/motor GETs followed by /api/status without independent failure handling. A single temporary HTTP 503 at startup rejected the async load handler, so automatic status polling never began. Later status poll failures updated only the banner and left the maintenance badge, critical drive/output telemetry and E-STOP toggle reporting cached state as live. If the previously cached E-STOP state was active, clicking the toggle could prepare an unverified rearm request.

## Changes and precise behavior
- PiServer/piserver/web/static/app.js: catch optional startup read failures individually with visible feedback; continue preview/status initialization and schedule read-only status retries. Render connection loss as offline/unverified in the toolbar, status dock and critical telemetry. Preserve last actual E-STOP state internally but mark accessible button aria-pressed mixed while unknown. On unverified E-STOP press always submit engagement {enabled:true}; never rearm until a successful server status read. Clear unverified presentation on valid status recovery. Do not assume a submitted STOP succeeded.
- PiServer/piserver/web/templates/index.html: status banner announces connection transitions via role=status and aria-live=polite; no geometry or layout change.
- PiServer/piserver/app.py: advance candidate from 0_4_33 to 0_4_34; no route logic changed.
- tools/check_browser_ui.py: hardware-free actual Flask template/Chromium tests for cold 503 startup across model/session/camera/motor/status, STOP engagement-only request under unknown status, automatic retry viability and successful restoration at 390, 768, 1024 and 1440px. All mutations remain intercepted 503. Previous browser checks remain active.
- docs/ui_regression_gate.md: document scoped coverage/limits.

## Anti-rollback
Read PiServer/server.py, current app creation, actual JS and templates, real browser fixture, versions, previous 4 PiServer patch notes (0.4.33/32/31/30) and fully green parent b379138. Preserved stored theme/layout keys, draggable square pad and status grid, settings save/readback controls, model/session deletion confirmation, existing E-STOP API and server-side hardware watchdog. No user config, recorded data, model, camera/motor service or inactive component files changed.

## Verification and limits
Candidate code and test source reviewed; exact CI must pass before declaring verified. Tests simulate disconnected GETs and rejected POSTs; they do not prove physical STOP or validate a real hardware network outage, Windows or owner-accepted screenshots. New failure-state UI is deliberately not a new motor safety mechanism. No count increase: implementation scope 35/56, Batch 4 unfinished.
