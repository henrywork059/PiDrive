# PiServer 0.4.37 — Batch 4 / UX75 model library refresh and recovery

## Request and root cause
Continue Batch 4 from e679901 (CI 45438129785, all four jobs passed). The explicit model Refresh button directly called an async read without a rejection handler. A disconnected request produced an unhandled promise rejection; successful refresh reset the chosen model to the active/first model even when the user's selection still existed. Overlapping reads could also render superseded model lists.

## Changed files and behavior
- PiServer/piserver/web/static/app.js: explicit Refresh handler reports read errors and retry guidance without clearing existing options. Successful explicit refresh retains a still-listed selection and reports success; removed selections fall back to the existing active/first rule. Request generation ignores superseded reads and errors. Initial and post-mutation refreshes retain their existing default selection and messages.
- PiServer/piserver/web/templates/index.html: existing model feedback becomes an accessible polite status region; no layout change.
- PiServer/piserver/app.py: version marker only.
- tools/check_browser_ui.py: actual Auto workspace Refresh interaction with synthetic GET failure, successful retry, preserved selection, removed selection fallback, real empty list and status region at all four widths. All POSTs intercepted.
- docs/ui_regression_gate.md: evidence and limits.

## Anti-rollback
Inspected live launcher, source and actual API response contract, current main roadmap, regression workflow and latest four notes 0.4.36/35/34/33. Preserved 0.4.36 status revision guard, 3500ms GET deadline, E-STOP/rearm, model mutation endpoints and exact-target deletion confirmation, settings and layout. No motor/AI algorithm, data, configuration or inactive component changes.

## Verification and limits
Parent CI green; exact new CI pending. Synthetic model names are not loaded or deleted; browser simulation does not establish physical STOP, network packet-loss resilience, native Windows or owner visual acceptance. Batch 4 remains open at 35/56.
