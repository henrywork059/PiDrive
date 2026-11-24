# PiSD 0.11.31 — Batch 4 / R35, R50 and UX75 failure-state truthfulness

## Request and root cause
Continue the active Batch 4 acceptance gate from verified 300f018 (CI 45397236501, four jobs and 16/16 browser viewports passed). The Settings STOP button directly invoked settingsApi without catching a rejected Promise. A synthetic or genuine unsuccessful HTTP response could create an unhandled page error, while an error payload with no code temporarily defaulted the global code display to PISD-OK-000.

## Exact changes
- PiSD/pisd/web/static/js/settings_tab.js: handle STOP API rejection, record the request as not confirmed, and explicitly show PISD-API-STOP-FAILED in the existing status/log display. Keep the same POST /api/control/stop request, server-side authorization, motor logic and global Space STOP implementation.
- PiSD/pisd/__init__.py: advance the unreleased candidate from 0.11.30 to 0.11.31.
- tools/check_browser_ui.py: test rejected Settings Save, visible failure detail, retry (second real intercepted request), enabled Save after failure, and rejected STOP status/absence of unhandled JavaScript errors at 390/768/1024/1440 widths.
- docs/ui_regression_gate.md: document this extra acceptance coverage and its limitations.

## Forward/anti-rollback review
Verified current development HEAD 300f018, canonical roadmap and R35/R50/UX75 acceptance criteria. Inspected the PiSD 0.11.30, 0.11.29, 0.11.28, 0.11.27 notes and current Settings template/JS, feedback helper, global Space STOP handler and shared Chromium test. No configuration, data, models, camera, motor algorithms, inactive components or visual styling changed. This patch does not confirm physical STOP success when the response fails, and does not change the emergency STOP request or require a confirmation dialog.

## Verification and limits
GitHub source inspection and test-code review performed. Baseline CI 45397236501 completed successfully before this patch. Full four-job CI on the new commit remains required; do not represent it as tested until its result is checked. Native Windows, physical Raspberry Pi safety acceptance and screenshot owner review remain pending. This patch contributes to Batch 4; it does not close R35/R36/R50/UX75 or increment the 35/56 progress count.
