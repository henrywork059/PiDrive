# PiSD 0.2.10 Patch Notes

## Request summary

Add a persistent settings manager and harden apply-to-all-tabs behaviour. Unify page styling under settings, keep the Manual Drive page compact, move logs into an expandable panel, keep the preview visible on common PC/iPad screens, and replace button-based driving with a drag pad.

## Cause / reason

The previous UI saved some values in browser localStorage, but the project needs one backend source of truth before more GUI features are added. The Manual Drive page also had too much status/log content and button controls were less suitable for smooth driving tests.

## Files changed / added

- `pisd/__init__.py`
- `pisd/app.py`
- `pisd/core/errors.py`
- `pisd/core/settings_manager.py`
- `pisd/web/templates/settings_tab.html`
- `pisd/web/static/css/settings_tab.css`
- `pisd/web/static/js/settings_tab.js`
- `pisd/web/templates/manual_drive.html`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/templates/panel_presentation.html`
- `pisd/web/static/js/panel_presentation.js`
- `pisd/web/static/css/panel_presentation_global.css`
- `pisd/web/static/js/panel_presentation_global.js`
- `scripts/test_settings_persistence.py`
- updated static validation scripts and docs

## Behaviour changed

- Added `config/runtime_settings.json` support via `SettingsManager`.
- Added settings endpoints:
  - `GET /api/settings`
  - `GET /api/settings/schema`
  - `POST /api/settings`
  - `POST /api/settings/apply`
  - `POST /api/settings/reset`
- Camera and motor apply endpoints now persist their current configs into runtime settings.
- Settings page now controls camera, motor, manual drive defaults, and panel presentation settings.
- Panel presentation settings are loaded from the backend when available and cached in browser storage as fallback.
- Shared presentation settings apply to all GUI pages.
- Manual Drive status is now a short status strip.
- Manual Drive log is hidden by default and expands with a button.
- Manual Drive uses a drag pad with pointer events; releasing the pad calls STOP.
- Preview sizing is more adaptive with max-height rules to reduce unnecessary scrolling on common PC and iPad screens.

## Error codes added

- `PISD-SET-001` settings file load failed
- `PISD-SET-002` settings file save failed
- `PISD-SET-003` invalid settings payload
- `PISD-SET-004` settings apply failed
- `PISD-SET-005` settings reset failed
- `PISD-TEST-020` settings persistence validation failed

## Verification performed

- `python3 -m compileall -q .`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/test_panel_presentation_page.py --static-only`
- `python3 scripts/test_main_dashboard.py --static-only`
- `python3 scripts/test_testing_server_gui.py --static-only`
- `python3 scripts/test_panel_testing_page.py --static-only`
- `python3 scripts/test_panel_api_contracts.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`

## Not verified here

- Real Raspberry Pi browser rendering.
- Real camera/motor hardware calls through the updated settings API.
- Live drag-pad movement on the physical car.

These should be tested on the Pi with wheels lifted before driving on the ground.
