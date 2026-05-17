# PiSD Presentation Development Instructions

PiSD has several GUI pages, but they must share one visual and layout system. Do not recreate panel styles separately on each page.

## Source of truth

Use these files as the presentation source of truth:

- `pisd/core/presentation_registry.py` — backend registry for presentation defaults, controls, page layout contracts, and development rules.
- `pisd/core/settings_manager.py` — persists user settings in `config/runtime_settings.json` and uses the registry defaults for `panel_presentation`.
- `pisd/web/static/js/panel_presentation_global.js` — loads saved settings from `/api/settings` and applies CSS variables/data attributes to every page.
- `pisd/web/static/css/pisd_design_system.css` — final shared CSS layer loaded last on every page.
- `pisd/web/static/css/unified_layout.css` — older recovery layer retained for compatibility. New cross-page decisions should go into `pisd_design_system.css`, not more page-specific overrides.

## Asset loading rule

Every GUI template must load static assets through:

```jinja2
{{ static_asset('css/example.css') }}
```

This adds the current PiSD version as a query string so browsers do not keep stale CSS/JS after a patch.

Every GUI page must load CSS in this order:

1. `panel_presentation_global.css` when the page uses shared presentation settings
2. page-specific CSS
3. `unified_layout.css`
4. `pisd_design_system.css` last

## Page-specific CSS rule

Page-specific CSS should only style the inside of its own controls. It should not redefine shared panel surfaces, buttons, page background, topbar shape, or cross-page grid logic.

Good page-specific CSS examples:

- drag-pad inner labels and crosshair details
- one panel's internal form grid
- camera preview inner media behaviour

Avoid page-specific CSS for:

- general panel/card border/radius/shadow
- global button shape
- whole-page topbar design
- semantic panel placement already defined by `pisd_design_system.css`

## Manual Drive fixed layout contract

Manual Drive is the user-facing driving page. Its layout must stay predictable.

Desktop / PC / iPad style:

```text
status  drive
preview drive
preview stop
log     log
```

This places the camera panel directly under the status panel, while the manual drag pad stays in the right-side control column.

Small screen order:

```text
status
preview
drive
stop
log
```

Saved presentation settings may resize panels and adjust density/spacing, but they must not move the camera panel into the control column or move manual controls below the camera unless the screen is narrow.

## Drag pad rule

The drag knob must track the pointer position. Use parent-relative `left/top` variables:

```text
--knob-left
--knob-top
```

Do not use `translate(calc(-50% + 100%))` style offsets for the knob because percentage translations are relative to the knob size, not the pad size.

## Settings rule

All user-adjustable presentation settings should be saved through the Settings page or Panel Presentation page, and persisted through:

```text
POST /api/settings/apply
```

Do not add a new independent browser-only setting store unless it is only a temporary fallback cache. The backend settings manager is the source of truth.

## Recording rule

Frame capture and recording must go through the recording API/service:

```text
POST /api/recording/capture
POST /api/recording/start
POST /api/recording/stop
```

Do not save image files directly from a page. See `docs/RECORDING_DATA.md` for the folder and metadata contract.

## Test before packaging

Run these checks after presentation changes:

```bash
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_recording_service.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

On the Pi, also check the real pages in a browser:

```text
/manual-drive
/settings
/testing
/dashboard
/panel-presentation
/panel-testing
```

## Common rollback risks

Before finalizing a patch, check that you did not:

- remove `pisd_design_system.css` from any template
- load `pisd_design_system.css` before `unified_layout.css`
- reintroduce unversioned `url_for('static', ...)` asset links
- move Manual Drive camera preview away from the status panel
- break the drag pad pointer/knob alignment
- make page-specific CSS override saved global presentation variables
- create a second set of presentation defaults outside `presentation_registry.py`
- write recordings/test outputs into patch zips
