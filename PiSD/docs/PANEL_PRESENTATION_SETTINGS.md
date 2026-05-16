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

The page writes settings to browser `localStorage` under:

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

- Settings are browser-local only for now.
- Server-side persistence can be added later if needed.
- The page does not change hardware configuration.
- It should not be used as the panel functionality/API test page; use `/panel-testing` for that.
