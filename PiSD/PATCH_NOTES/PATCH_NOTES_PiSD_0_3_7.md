# PiSD 0.3.7 Patch Notes — Responsive Layout System

## Request summary

The user reported that page/panel presentation had become inconsistent and that the camera panel still did not reliably appear under the status panel. The user requested a review of all panels, windows, tabs, and pages, plus development instructions and a shared source for style/presentation so future patches do not recreate styling differently and cause layout bugs.

## Cause / root cause

Recent GUI patches had multiple overlapping CSS layers:

- page-specific CSS files
- `unified_layout.css`
- `pisd_design_system.css`
- saved panel presentation settings applied through JavaScript

Several of these layers could influence grid placement, and some broad adaptive-panel rules were too powerful. This meant panel size/style controls could accidentally fight the intended semantic layout. The Manual Drive page was especially fragile because previous CSS tried to place status, preview, drive, stop, and log panels from more than one file.

## Files changed

New files:

- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/scripts/test_responsive_layout_contract.py`
- `PiSD/docs/RESPONSIVE_LAYOUT_SYSTEM.md`

Updated files:

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/core/presentation_registry.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/static/js/panel_presentation_global.js`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/scripts/test_ui_presentation_consistency.py`
- `PiSD/docs/PRESENTATION_DEVELOPMENT.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/README.md`

## Exact behavior changed

- Added `pisd_layout_system.css` as the final layout authority loaded last on every GUI page.
- Added page body classes so shared layout rules can target pages consistently:
  - `front-page`
  - `manual-drive-page`
  - `settings-page`
  - `testing-page`
  - `dashboard-page`
  - `panel-presentation-page`
  - `panel-testing-page`
- Manual Drive now has a stricter semantic layout:

```text
wide / PC / iPad landscape:
status  status
preview drive
preview stop
log     log

small / phone / portrait:
status
preview
drive
stop
log
```

- Status is full-width at the top on wide layouts.
- Camera Preview is directly under Status in the main column.
- Manual Control stays in the right control column.
- Emergency Stop stays below Manual Control.
- The log remains hidden until opened.
- Settings, Testing, Dashboard, Panel Presentation, and Panel Testing pages now have shared responsive page-grid rules in the final layout file.
- Presentation settings can still tune density, font scale, gap, radius, preview fit, button scale, console height, and role weights, but they should no longer reorder safety-critical page regions.
- The presentation registry now lists the final CSS loading order and responsive layout contract.
- Runtime settings now normalise new presentation fields:
  - `layoutSystem`
  - `semanticLayoutLock`
  - `previewPriority`
  - `topbarMode`
- Added test code `PISD-TEST-023` for responsive layout contract failures.

## Verification actually performed

Locally verified without Pi hardware:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_responsive_layout_contract.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

All listed local checks passed.

## Not verified here

- Real Raspberry Pi browser rendering.
- Real camera preview under the new layout on the Pi browser.
- Real motor output or recording behavior; this patch intentionally changes presentation/layout only.

## Known limits / next steps

- The Pi browser should be hard-refreshed or opened in a private window after applying this patch, because previous CSS files may be cached.
- If the user still sees an old layout, first confirm that the page source includes `css/pisd_layout_system.css?v=0.3.7` and that browser cache is cleared.
- Future GUI pages must follow `docs/RESPONSIVE_LAYOUT_SYSTEM.md` and must load `pisd_layout_system.css` last.
