# PiSD 0.2.6 Patch Notes

## Request summary

Add a front page that lets the user select a mode/page tab before entering the GUI. The required tabs are a settings tab and a testing tab, and every tab/page must include a button/link to return to the front page.

## Cause / reason

The previous state made `/` load the main dashboard shell directly. Before continuing final GUI development, the project needs a clearer routing layer so users can choose between settings, testing, dashboard, and panel-test workspaces.

## Files changed / added

- `PiSD/pisd/app.py`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/static/css/front_page.css`
- `PiSD/pisd/web/static/js/front_page.js`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/css/settings_tab.css`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/scripts/test_front_page_tabs.py`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/scripts/test_testing_server_gui.py`
- `PiSD/scripts/test_api_endpoints.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/README.md`

## Behavior changed

- `/` now loads the front page / mode selector.
- `/settings` loads the new settings tab.
- `/testing` remains the API/settings testing tab.
- `/dashboard` now loads the actual dashboard shell that was previously at `/`.
- `/panel-testing` remains the panel testing lab.
- Settings, testing, dashboard, and panel-testing pages now include a **Back to Front Page** link.

## Error codes

- Added `PISD-TEST-016` for front page / tab navigation contract validation failures.

## Verification actually performed

- Python compile check for all PiSD Python files.
- `python3 PiSD.py --status-only`.
- `python3 scripts/check_error_reporting.py`.
- `python3 scripts/test_front_page_tabs.py --static-only`.
- `python3 scripts/test_main_dashboard.py --static-only`.
- `python3 scripts/test_testing_server_gui.py --static-only`.
- `python3 scripts/test_panel_testing_page.py --static-only`.
- `python3 scripts/test_panel_api_contracts.py --static-only`.
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`.

## Not verified here

- Raspberry Pi browser rendering.
- Flask route execution if Flask is not installed in the packaging environment.
- Real camera or motor hardware.

## Known limits / next steps

- The settings tab applies settings through existing APIs but does not yet persist a full user profile.
- The front page is a routing shell; final UI polish and layout persistence should come later.
