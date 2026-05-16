# PiSD 0.2.8 Patch Notes — Compact UI and Panel Presentation Settings

## Request summary

The user requested a compact UI update before continuing the GUI work:

- reduce the large top title/header space
- make pages more compact
- remove tab-changing buttons from pages because the user can select pages from the front page
- do not rename or replace `/panel-testing`
- add a new page where users can set the presentation/style/size of panels
- saved panel presentation settings should apply to other pages and tabs

## Cause / reason

The existing GUI shell pages used large headers and cross-page navigation buttons. This took screen space away from the testing/control panels, especially on smaller displays. The panel testing page was also doing two jobs: stress testing planned panels and holding layout/style controls. The new split keeps `/panel-testing` as a functional panel/API testing lab while adding a separate `/panel-presentation` page for visual presentation settings.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/static/css/front_page.css`
- `PiSD/pisd/web/static/css/panel_presentation.css`
- `PiSD/pisd/web/static/css/panel_presentation_global.css`
- `PiSD/pisd/web/static/js/panel_presentation.js`
- `PiSD/pisd/web/static/js/panel_presentation_global.js`
- `PiSD/scripts/test_front_page_tabs.py`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/scripts/test_panel_presentation_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/docs/PANEL_PRESENTATION_SETTINGS.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/README.md`

## Exact behavior changed

### Added new route

```text
/panel-presentation
```

This is a new browser-local presentation settings page. It does not replace `/panel-testing`.

### Preserved existing route

```text
/panel-testing
```

This remains the panel stress/API contract testing lab.

### Added new API manifest route

```text
GET /api/panel-presentation/manifest
```

Returns the presentation-settings storage key, supported controls, and the pages affected by the saved presentation settings.

### Added shared panel presentation settings

New shared CSS/JS:

```text
pisd/web/static/css/panel_presentation_global.css
pisd/web/static/js/panel_presentation_global.js
```

Saved settings use browser `localStorage`:

```text
pisd.panelPresentation.v1
```

These settings currently apply to:

```text
/
/settings
/testing
/dashboard
/panel-testing
/panel-presentation
```

Settings include:

- theme
- layout mode
- density
- font scale
- panel gap
- panel corner radius
- border strength
- shadow strength
- minimum panel width
- preview aspect ratio

### Made the front page more compact

Reduced:

- front-page outer padding
- hero/header size
- card height
- card text size
- status strip spacing
- output console height

### Removed tab-changing buttons from inner pages

Pages now keep `Back to Front Page` plus local actions such as refresh, STOP, and page-specific controls. Cross-tab buttons such as Settings/Testing/Dashboard/Panel Testing were removed from page headers.

### Added error code

```text
PISD-TEST-018
```

Used for panel presentation settings validation/import failures.

## Verification actually performed

Performed locally in the packaging environment:

```bash
python3 -m py_compile PiSD.py $(find pisd scripts -name '*.py' -print)
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_testing_server_gui.py --static-only
python3 scripts/test_panel_testing_page.py --static-only
python3 scripts/test_panel_api_contracts.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

All listed checks passed with `PISD-OK-000`.

## Not verified here

- Browser interaction on the Raspberry Pi display
- Flask route rendering on the Pi
- Hardware camera or motor behavior

This patch is UI/static/route-focused and does not change camera or motor service logic.

## Known limits / next steps

- Panel presentation settings are browser-local only for now.
- Server-side persistent UI profile saving can be added later.
- The compact UI should be reviewed on phone/tablet/laptop screen sizes before locking final GUI layout.
- `/panel-testing` still has its own internal style controls for testing; `/panel-presentation` is the global saved presentation page.
