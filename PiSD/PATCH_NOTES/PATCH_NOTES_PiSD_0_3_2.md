# PiSD 0.3.2 Patch Notes — Unified Page and Panel Presentation Recovery

## Request summary

The user reviewed the PiSD GUI pages after `0.3.1` and reported that the presentation was worse than the previous version. The requested fix was to unify styles across every page, make better decisions for page and panel layouts, and review panel presentation, visibility, and layout behaviour.

The user screenshots showed these main issues:

- Manual Drive panels overlapped/competed for space, with controls sitting over the preview area.
- Settings used too much vertical space and had large blank areas due to dense/weighted grid placement.
- Testing, Dashboard, Panel Presentation, and Settings pages had inconsistent topbars, panel spacing, button sizing, and panel shapes.
- The shared panel-weight system could override page-specific layout decisions too aggressively.

## Cause / root cause

`0.3.1` added role-based horizontal/vertical panel weights into the shared global presentation stylesheet. Because that stylesheet used broad `[data-panel-role]` selectors and `!important` grid rules, it affected different pages in different ways. Some pages were designed with their own explicit grids, but the shared weighting layer overrode those grids and caused inconsistent layouts.

## Files changed / added

### Added

- `PiSD/pisd/web/static/css/unified_layout.css`
- `PiSD/scripts/test_ui_presentation_consistency.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_2.md`

### Updated

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/PANEL_PRESENTATION_SETTINGS.md`

## Exact behaviour changed

### Shared visual layer

Added `unified_layout.css`, loaded last on every GUI page. It standardises:

- topbar height and spacing
- page background
- panel/card surface style
- button shape and size
- `PISD-*` status-code pill style
- form spacing
- console/log sizing
- responsive breakpoints

This file intentionally sits after each page stylesheet so it can recover from page-specific or older shared CSS that causes layout regressions.

### Manual Drive

- Status is kept above the camera preview on PC/iPad layouts.
- Preview takes the main horizontal space.
- Drag pad and STOP panels use a side column on wide screens.
- Log remains hidden/expandable.
- On smaller screens, panels stack in the safe order: status, preview, drag pad, STOP, log.
- The broad global panel-weight selectors are overridden on Manual Drive so they do not cause panel overlap.

### Settings

- Settings now uses a deliberate three-region desktop grid:
  - save/apply and motor controls on the left
  - page/panel style controls in the centre
  - manual defaults and camera settings on the right
  - last response below the main controls
- This removes the large blank areas caused by dense grid auto-placement.
- On smaller screens, the settings panels stack cleanly.

### Testing page

- The testing server page now uses a compact 12-column lab layout on wide screens.
- Camera preview, FPS test, settings forms, motor tests, smoke test, API caller, and status panels are placed more predictably.
- On tablets/phones, the page stacks to one column.

### Main Dashboard

- Dashboard panels now use a deliberate desktop arrangement:
  - runtime status left
  - camera preview centre
  - movement/channel/safety controls right
  - error/log panels below
- Broad panel role weighting no longer disrupts the dashboard grid.

### Panel Presentation and Panel Testing

- Panel Presentation now keeps style controls beside the preview on PC/iPad layouts and stacks on small screens.
- Panel Testing keeps its controls as a side rail on wide screens and stacks normally on smaller screens.

### Error code added

- `PISD-TEST-021` — unified UI presentation consistency validation failed.

## Existing behaviour preserved

- No camera service code was changed.
- No motor service code was changed.
- No API behaviour was changed.
- Manual Drive drag pad logic was not changed.
- Settings manager behaviour was not changed.
- `/panel-testing` remains the panel testing lab.
- `/panel-presentation` remains the panel style/settings page.
- Existing page-specific CSS remains in place; the new unified layer only controls the final visible layout.

## Verification actually performed

Local checks performed in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Results:

- Python compile passed.
- Status-only check returned `PISD-OK-000`.
- Error-reporting check passed.
- Unified UI presentation source/static check passed.
- Manual Drive static/source check passed.
- Panel Presentation static/source check passed.
- Front page/settings static/source check passed.
- Settings persistence test passed.
- Standard validation passed with API/camera/motor skipped.

## Not verified here

- Real Raspberry Pi browser rendering.
- Browser visual comparison on actual PC and iPad screens.
- Real camera preview height in the Pi browser.
- Real motor drag-pad movement.

## Recommended Pi-side checks

After applying the patch:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then visually check:

```text
http://<pi-ip>:5050/
http://<pi-ip>:5050/manual-drive
http://<pi-ip>:5050/settings
http://<pi-ip>:5050/testing
http://<pi-ip>:5050/dashboard
http://<pi-ip>:5050/panel-presentation
http://<pi-ip>:5050/panel-testing
```

The key visual checks are:

- Manual Drive no longer overlaps controls onto the preview.
- Manual Drive status remains above preview on PC/iPad layouts.
- Settings has no large blank middle area caused by panel weights.
- Topbars look similar across all pages.
- Panels have consistent spacing, borders, radius, and button sizing.
- Phone/tablet widths still stack cleanly.
