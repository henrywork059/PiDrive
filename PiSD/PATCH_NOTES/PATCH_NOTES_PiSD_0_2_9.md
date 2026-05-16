# PiSD 0.2.9 Patch Notes — Manual Drive Page and Shared Panel Presentation Settings

## Request summary

Add a front-page Manual Drive tab/page for easy car control, ensure settings are saved and applied across tabs, and improve the panel presentation page so it better serves as the place for tuning panel styles.

## Cause / design reason

PiSD already had separate testing, settings, dashboard, panel-testing, and panel-presentation pages. The dashboard was still a broader shell, while the user needed a simpler page focused on real manual driving: camera preview, key status, manual pad, and STOP.

The panel presentation page also needed more controls for practical panel style tuning, and saved style choices needed to apply consistently across all GUI pages.

## Files changed / added

### Added

- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_9.md`

### Updated

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/web/templates/front_page.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/templates/panel_presentation.html`
- `PiSD/pisd/web/static/css/front_page.css`
- `PiSD/pisd/web/static/css/panel_presentation.css`
- `PiSD/pisd/web/static/css/panel_presentation_global.css`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/pisd/web/static/js/panel_presentation.js`
- `PiSD/pisd/web/static/js/panel_presentation_global.js`
- `PiSD/scripts/test_front_page_tabs.py`
- `PiSD/scripts/test_panel_presentation_page.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/PANEL_PRESENTATION_SETTINGS.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/ERROR_CODES.md`

## Exact behavior changed

### Manual Drive page

Added a new route:

```text
/manual-drive
```

The front page now includes a Manual Drive card.

The Manual Drive page includes:

- live camera preview using `/video_feed`
- important status only: hardware, camera, motor, FPS, current JSON status
- manual driving pad: forward, left, right, reverse, STOP
- speed slider
- steer-strength slider
- motor-output safety checkbox
- top and large STOP buttons that remain available even when drive controls are locked
- last API response / `PISD-*` code panel

Movement buttons are disabled by default. If the page is not armed, manual drive attempts are blocked in the browser with `PISD-MOT-008`.

### Settings tab persistence

The settings tab now saves camera and motor form values into browser localStorage:

```text
pisd.runtimeSettings.v1
```

Submitting camera or motor settings still applies them through the backend API:

```text
POST /api/camera/apply
POST /api/motor/apply
```

Those runtime settings affect all tabs because the tabs use the same backend camera and motor services.

### Panel presentation settings

The existing `/panel-presentation` page was improved with extra style controls:

- preview fit
- panel padding
- panel header mode
- button size
- console height
- card accent strength
- auto-save changes globally

The shared panel-presentation settings now also apply to `/manual-drive`.

### Front page compactness

The front page mode cards were adjusted to fit the added Manual Drive option without making the page taller than needed.

### Error codes

Added:

```text
PISD-TEST-019
```

This is used for manual-drive page contract validation failures.

## Verification actually performed

Performed locally in the packaging environment:

```bash
python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

Observed all listed static/source validation commands passing with `PISD-OK-000`.

## Verification not performed

Not verified in this environment:

- Flask route execution, because Flask is not installed in the packaging environment.
- Raspberry Pi browser rendering.
- Real camera preview.
- Real motor movement.

These should be checked on the Raspberry Pi after applying the patch.

## Suggested Pi-side validation

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/run_standard_validation.py --hardware --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/
```

Then check:

- front page includes Manual Drive
- `/manual-drive` loads
- camera preview starts
- STOP always works
- drive buttons remain locked until the safety checkbox is enabled
- `/panel-presentation` settings apply on `/manual-drive` and other pages

## Known limits / next steps

- Settings persistence is browser-local only for now.
- Server-side settings persistence can be added later if required.
- Manual Drive page is intentionally simple; final styling/docking/layout tools should be added only after hardware behavior is confirmed.
