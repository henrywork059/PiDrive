# PiSD 0.5.11 Patch Notes

## Request summary
Review the current PiSD project after the recent 0.5.x AI Mode and overlay patches, checking for coding-level conflicts, bugs, or rollback risk.

## Cause / root cause
The active runtime correctly replaced scripted Autopilot with AI Mode in 0.5.2, but two legacy validation scripts still expected the removed scripted Autopilot behaviour. They also referenced old Autopilot-specific error constants that are no longer present in the shared error registry. This created a test-suite conflict even though the runtime shim itself was intentionally retired.

## Files changed
- `pisd/__init__.py`
- `scripts/test_autopilot_service.py`
- `scripts/test_autopilot_page.py`
- `README.md`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_5_11.md`

## Exact behaviour changed
- `scripts/test_autopilot_service.py` now validates the deprecated Autopilot shim:
  - status reports `deprecated: true`
  - `start()` is blocked and points to `/ai-mode`
  - `stop()` is a safe no-op
  - no scripted movement profile is expected or accepted
- `scripts/test_autopilot_page.py` now validates the legacy Autopilot compatibility page/static files:
  - old `/autopilot` path opens AI Mode
  - old static CSS/JS are retired redirect/compatibility files
  - no old Autopilot API or movement controls are required
- Version bumped to `0.5.11`.

## Verification actually performed
- Reconstructed current PiSD from `PiSD_0_5_0.zip` plus patches `0_5_1` through `0_5_10` before editing.
- Reviewed latest patch notes `0_5_8`, `0_5_9`, and `0_5_10` for rollback risk.
- `python3 -m compileall pisd scripts PiSD.py`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/test_main_dashboard.py --static-only`
- `python3 scripts/test_recording_service.py`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_ai_drive_service.py`
- `python3 scripts/test_autopilot_service.py`
- `python3 scripts/test_autopilot_page.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Known limits / next steps
- Full Flask route validation was not run here because Flask is not installed in this container.
- Real Pi camera/motor hardware behaviour was not tested here.
- One harmless duplicate unreachable `return jsonify(panel_contracts_payload())` remains in `pisd/app.py`; it does not affect runtime but can be cleaned in a future small tidy patch.
