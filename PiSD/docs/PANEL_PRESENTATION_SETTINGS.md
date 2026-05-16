# PiSD Panel Presentation Settings

`/panel-presentation` is a separate presentation-settings page for the PiSD GUI.
It does not replace `/panel-testing`.

## Purpose

Use this page to tune how panels look before the final GUI grows larger:

- theme: dark, light, high contrast
- layout mode: adaptive, single column, dense, wide
- density: compact, comfortable, spacious
- font scale
- panel gap
- panel corner radius
- border strength
- shadow strength
- minimum panel width
- camera preview aspect ratio
- adaptive panel sizing on/off
- role-based horizontal and vertical panel weights for status, preview, controls, settings, and logs

The page saves settings through the backend settings manager (`config/runtime_settings.json`) and also keeps a browser fallback/cache under:

```text
pisd.panelPresentation.v1
```

The shared files below apply saved settings across the current PiSD GUI pages:

```text
pisd/web/static/css/panel_presentation_global.css
pisd/web/static/js/panel_presentation_global.js
```

Pages currently loading the shared presentation settings:

```text
/
/settings
/testing
/dashboard
/panel-testing
/panel-presentation
```

## Important routing note

`/panel-testing` stays as the panel stress/API contract lab.

`/panel-presentation` is only for controlling panel style and size presentation.

## How to test

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_panel_presentation_page.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/panel-presentation
```

Change settings, click `Save for all pages`, then open the other pages from the front page.

Expected result:

```text
OK   PISD-OK-000   panel_presentation.source_contract - panel presentation page includes controls, save/apply/export/import, and global style application
```

## Known limits

- The page does not change hardware configuration.
- It should not be used as the panel functionality/API test page; use `/panel-testing` for that.
- The browser cache is only a fallback. The backend settings manager is the source of truth when available.

## 0.2.9 expanded style controls

Additional controls were added so this page better fits its purpose as the panel presentation/settings tab:

- preview fit: `contain`, `cover`, or `fill`
- panel padding scale
- panel header mode: `standard`, `compact`, or `minimal`
- button size scale
- console/log maximum height
- card accent strength: `subtle`, `strong`, or `none`
- auto-save changes globally

Auto-save is enabled by default. When it is enabled, changing a control saves the setting immediately to browser localStorage and applies it to all PiSD GUI tabs when they open.

The shared presentation settings now apply to:

```text
/
/manual-drive
/settings
/testing
/dashboard
/panel-testing
/panel-presentation
```

## 0.3.1 adaptive panel weights

`PiSD_0_3_1_patch` adds role-based horizontal and vertical panel weights. These make it easier to manage how panels use space on PC, iPad, and phone screens without editing each page separately.

Roles currently supported by the shared presentation system:

```text
status
preview
control / drive
settings
log
```

The Manual Drive page now places the compact status panel above the camera preview on PC/iPad layouts. The preview uses available screen height so the full frame is visible on most PC and iPad screens without extra page scrolling.

## PiSD 0.3.2 layout recovery notes

The shared page style now has a final `unified_layout.css` layer loaded after each page's original stylesheet. This keeps older per-page styles available while making the final visible layout consistent across pages.

Current layout decisions:

- Manual Drive: status is above the preview, preview uses the main horizontal space, drag pad and STOP controls sit in the side column on PC/iPad layouts, and all panels stack cleanly on small screens.
- Settings: the save/apply panel, style controls, camera settings, motor settings, manual defaults, and response panel are placed in a deliberate desktop grid instead of being left to dense auto-placement.
- Testing: camera preview/FPS/API cards are arranged in a compact multi-column lab view on wide screens and stack on tablets/phones.
- Dashboard: status, preview, bench controls, channel calibration, safety stop, and logs use fixed responsive regions rather than uncontrolled panel weights.
- Panel Presentation: the control form stays beside the live preview on PC/iPad screens and stacks on smaller screens.
- Panel Testing: the environment controls stay in a side rail on wide screens and become a normal top section on smaller screens.

Panel presentation settings still control density, radius, gap, font scale, preview fit/aspect, console height, and button scale. The unified layer uses those variables but prevents saved panel weights from breaking page structure.

## 0.3.4 presentation source-of-truth update

From `PiSD_0_3_4`, shared presentation decisions should be defined through:

- `pisd/core/presentation_registry.py`
- `pisd/web/static/css/pisd_design_system.css`
- `pisd/web/static/js/panel_presentation_global.js`
- `config/runtime_settings.json` through the settings manager

The Panel Presentation page is for changing saved settings. It should not become a second layout engine. The design-system CSS is loaded last on every GUI page and keeps core page layout contracts stable while still allowing saved density, radius, gap, font, preview-fit, and weight tuning.
