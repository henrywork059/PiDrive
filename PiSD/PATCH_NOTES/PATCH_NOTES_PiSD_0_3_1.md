# PiSD 0.3.1 Patch Notes — Adaptive Panel Layout Review

## Request summary

The user requested a presentation/layout patch after the `PiSD_0_3_0` stable baseline:

- On PC and iPad layouts, the Manual Drive status panel should be placed above the preview panel.
- Panels should use horizontal space more intelligently according to the device.
- Add horizontal and vertical panel size weighting so panel sizing can be easier to manage.
- Review current panel/tab presentation, visibility, and style behaviour.

## Cause / design reason

The previous UI already had shared presentation settings, but panel sizing was mainly controlled by generic grid/min-width rules. That made it harder to deliberately give more space to important panel types such as live preview, compact status, controls, and logs.

The Manual Drive page also placed the preview before status in the markup/layout, so the user had to look away from the preview area to see compact running status on larger displays.

## Files changed

- `PiSD/README.md`
- `PiSD/docs/PANEL_PRESENTATION_SETTINGS.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/testing_server.html`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/css/panel_presentation.css`
- `PiSD/pisd/web/static/css/panel_presentation_global.css`
- `PiSD/pisd/web/static/css/settings_tab.css`
- `PiSD/pisd/web/static/js/panel_presentation_global.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_panel_presentation_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_1.md`

## Behaviour changed

### Manual Drive layout

- The Manual Drive status panel is now before/above the camera preview in the page structure.
- On PC/iPad-style widths, Manual Drive uses a 12-column adaptive layout:
  - status panel above preview on the left/main area
  - preview panel below status and larger than supporting panels
  - drag pad and safety panels on the right on wider screens
  - stacked single-column layout on phone-sized screens
- The preview panel now uses available screen height more efficiently so the full preview is visible on most PC/iPad screens without unnecessary page scrolling.

### Shared weighted-panel system

Added shared role-based panel weight settings:

- `statusPanelHWeight`
- `statusPanelVWeight`
- `previewPanelHWeight`
- `previewPanelVWeight`
- `controlPanelHWeight`
- `controlPanelVWeight`
- `settingsPanelHWeight`
- `settingsPanelVWeight`
- `logPanelHWeight`
- `logPanelVWeight`
- `adaptivePanels`

Supported panel roles:

- `status`
- `preview` / `camera`
- `control` / `drive`
- `settings`
- `log`

These settings are applied through the shared `panel_presentation_global.css/js` system.

### Settings and Panel Presentation pages

- The Settings page now exposes panel weight controls.
- The Panel Presentation page now exposes panel weight controls.
- Saved settings still go through the backend settings manager when available and browser local storage as fallback/cache.
- The settings manager now clamps panel weights safely between `1` and `4`.

### Existing behaviour preserved

- No camera-service or motor-service hardware behaviour was changed.
- `/panel-testing` remains unchanged as the panel/API lab.
- `/panel-presentation` remains the page for style/presentation settings.
- Manual Drive log remains hidden by default and expands only when requested.
- STOP controls remain available.

## Verification actually performed

Local checks performed in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Results:

- Python compile passed.
- Status-only check passed with `PISD-OK-000`.
- Error-reporting check passed.
- Manual Drive static/source checks passed, including the new status-above-preview check.
- Panel Presentation static/source checks passed.
- Front page/settings tab checks passed.
- Settings persistence test passed, including rejection of a bad payload with `PISD-SET-003`.
- Standard validation passed with API/camera/motor skipped.

## Not verified here

- Real Pi browser rendering on PC/iPad/phone sizes.
- Real camera preview height behaviour on the Pi display/browser.
- Real hardware motor operation.

## Recommended Pi-side checks

After applying the patch on the Pi:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then open:

```text
http://<pi-ip>:5050/manual-drive
http://<pi-ip>:5050/panel-presentation
http://<pi-ip>:5050/settings
```

Check visually:

- status is above preview on PC/iPad layouts
- preview is fully visible without unnecessary scrolling on common PC/iPad screens
- drag pad remains easy to use
- panel weights saved in Settings/Panel Presentation apply across tabs
- phone layout still stacks cleanly
