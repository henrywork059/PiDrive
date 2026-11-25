# PiServer 0.4.42 — Batch 4 / R35 visual-only style preview

## Request and cause
Continue from 174026c, verified all five Linux/Windows jobs. Style settings included eight example buttons/number inputs with no real action in the keyboard sequence; example fields could also accept edits that do not affect settings.

## Changed files
- PiServer/piserver/web/templates/index.html: mark only eight example controls inert and clarify the sample is visual-only; leave actual controls, CSS, preview layout and scroll container unchanged.
- PiServer/piserver/web/static/app.js: existing style-dialog focus trap excludes inert descendants.
- PiServer/piserver/app.py: version marker only.
- PiServer/tests/test_accessibility_r35.cjs: retain existing checks and add sample isolation and trap checks.
- tools/check_browser_ui.py: actual native Tab traversal, assert no sample receives focus and real style inputs, Reset and Save remain reachable, at the existing four viewport widths.
- docs/ui_regression_gate.md: scoped verification record.

## Anti-rollback and verification
Reviewed current launcher, template, modal handlers, browser fixture, CSS, current regression workflows and notes 0.4.41/40/39/38. No changes to API, saved settings, model manifest, recording, motor, STOP, layout preset or inactive component behavior. Parent Linux 45555698348 and Windows 45555698560 verified successful; exact new candidate CI pending. Source checks performed; new tests not yet executed. No proposal closure, hardware, owner visual approval or release claimed.
