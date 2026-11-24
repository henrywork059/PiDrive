# PiServer 0.4.33 — Batch 4 / R36 status metric legibility

## Request and root cause
Real Chromium captures from verified CI 45397236501 showed Status metric labels and values overlapping adjacent card borders. The issue was present in the narrow desktop Status dock and smaller responsive layouts. The scrollable Status grid's automatic rows could shrink below the intrinsic height of a label and value.

## Files changed / behavior
- PiServer/piserver/web/static/styles.css: set grid-auto-rows: max-content on the existing Status dock metric grid, so whole cards scroll instead of compressing below their content. Existing saved panel geometry, theme customization, layout settings, drag-pad dimensions and responsive breakpoints are not changed.
- PiServer/piserver/app.py: advance the unreleased candidate from 0_4_32 to 0_4_33.
- tools/check_browser_ui.py: test that actual rendered Status metric cards do not clip their content at 390, 768, 1024 and 1440 px.
- docs/ui_regression_gate.md: record observed screenshot defect and added regression check.

## Baseline and rollback assessment
Direct parent ba21198 (PiSD 0.11.31) passed the four-job regression gate in CI 45415572994. Reviewed PiServer 0.4.32, 0.4.31, 0.4.30 and 0.4.29 notes, current CSS, HTML, application version and panel layout implementation. No runtime control, STOP, motor/camera, recording, persistent settings, inactive components or model behavior changed.

## Verification and limitations
Actual screenshots from CI 45397236501 reviewed, revealing a defect outside the original 16 passing geometry checks. The new test is committed for the exact-candidate CI; its result is pending. After the gate, screenshot review and owner acceptance remain separate. No physical hardware or native Windows acceptance was performed. No R36 or Batch 4 completion count increment is claimed.
