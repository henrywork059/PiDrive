# PiSD 0.3.4 Patch Notes — Shared Presentation Source of Truth and Manual Drive Layout Fix

## Request summary

The user reported that after the previous presentation patches, the Manual Drive page still did not place the camera panel directly under the status panel. The user also asked to review all panels, windows, tabs, and pages again, add development instructions, and create a stable file/source of truth for styles and presentation so each page does not remake its own style and cause differences or layout bugs.

## Cause / root cause

The GUI had multiple presentation layers:

- page-specific CSS files
- `panel_presentation_global.css`
- `unified_layout.css`
- saved panel-presentation settings
- role/weight selectors added in earlier patches

Although `0.3.2` and `0.3.3` tried to recover the layout, there was still too much duplicated layout authority. In particular, older page CSS and shared adaptive panel rules could still compete with the intended Manual Drive semantic layout. Browser-side stale CSS caching could also make a newly patched stylesheet appear unchanged.

## Files changed / added

### Added

- `PiSD/pisd/core/presentation_registry.py`
- `PiSD/pisd/web/static/css/pisd_design_system.css`
- `PiSD/docs/PRESENTATION_DEVELOPMENT.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_4.md`

### Updated

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_ui_presentation_consistency.py`
- `PiSD/docs/PANEL_PRESENTATION_SETTINGS.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/README.md`

## Exact behaviour changed

### Shared presentation source of truth

Added `pisd/core/presentation_registry.py` as the backend presentation registry. It defines:

- shared panel-presentation defaults
- allowed presentation controls
- design-system asset order
- page layout contracts
- development rules for future GUI work

`settings_manager.py` now imports the presentation defaults from this registry instead of keeping a separate duplicate block of panel-presentation defaults.

### Final design-system CSS layer

Added `pisd/web/static/css/pisd_design_system.css`, loaded last on every GUI page. It is now the final shared presentation layer for:

- topbar consistency
- panel/card surfaces
- button/pill shapes
- page shell widths and gaps
- Manual Drive semantic placement
- Settings layout
- Dashboard layout
- Testing layout
- Panel Presentation / Panel Testing layout

Future cross-page style decisions should go into this file, not into separate page-specific overrides.

### Manual Drive layout contract

The Manual Drive page is now explicitly locked to this PC/iPad layout:

```text
status status
preview drive
preview stop
log log
```

This means:

- the status panel stays at the top
- the camera panel is directly below the status panel
- the drag/manual-control panel is in the right control column
- the emergency STOP panel is below the manual-control panel
- the log spans the page only when expanded

On narrow screens, the order remains:

```text
status
preview
drive
stop
log
```

Saved presentation settings may tune density, radius, gap, font scale, preview fit, and weights, but they should not move the Manual Drive camera panel out from under the status panel.

### Versioned static assets and cache safety

All GUI templates now use `static_asset(...)` instead of direct `url_for('static', ...)` calls. The helper adds the PiSD version query parameter to static CSS/JS links, reducing stale browser-cache issues after a patch.

The Flask app now also adds no-store cache headers for `/testing/static/*` assets.

### New presentation manifest API

Added:

```text
GET /api/presentation/manifest
```

This reports the shared presentation registry, design-system assets, page layout contracts, and development rules.

The existing `/api/panel-presentation/manifest` now uses the same registry data for its controls and layout contracts.

### Development instructions

Added `docs/PRESENTATION_DEVELOPMENT.md` with rules for future GUI work, including:

- use `pisd_design_system.css` for shared layout and style
- do not remake panel/card/button styles on each page
- keep page-specific CSS limited to internal component details
- load `pisd_design_system.css` last
- keep Manual Drive status -> preview -> controls order
- run the presentation regression tests before packaging

## Existing behaviour preserved

- No camera-service logic changed.
- No motor-service logic changed.
- No manual drag-pad API logic changed.
- No settings API contract changed.
- No `/panel-testing` route rename or behaviour change.
- Existing saved `runtime_settings.json` values remain compatible.
- Panel-presentation controls still save through the settings manager.

## Verification actually performed

Local verification performed in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Results:

- Python compile passed.
- Status-only check returned `PISD-OK-000`.
- Error-reporting check passed.
- Manual Drive static/source contract passed.
- UI presentation consistency static/source contract passed.
- Panel Presentation static/source contract passed.
- Front page/settings static/source contract passed.
- Settings persistence test passed, including rejection of bad settings with `PISD-SET-003`.
- Standard validation passed with API/camera/motor skipped.

## Not verified here

- Real browser rendering on the Raspberry Pi.
- Real PC/iPad visual layout after browser cache refresh.
- Flask route execution in this packaging environment because Flask is not installed here.
- Real hardware camera or motor behaviour; this patch is presentation/layout only.

## Recommended Pi-side checks

After applying the patch on the Pi:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard-refresh the browser and check:

```text
http://<pi-ip>:5050/manual-drive
http://<pi-ip>:5050/settings
http://<pi-ip>:5050/testing
http://<pi-ip>:5050/dashboard
http://<pi-ip>:5050/panel-presentation
http://<pi-ip>:5050/panel-testing
```

For Manual Drive, confirm visually:

- status panel is the top row
- camera panel is directly under the status panel
- manual drag pad is on the right side on PC/iPad screens
- emergency stop is below the drag pad
- log stays hidden until opened

If the browser still shows the old layout, do a hard refresh or open in a private/incognito window because earlier CSS may still be cached locally.
