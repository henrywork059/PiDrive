# PiSD Panel Testing GUI

## Purpose

`PiSD_0_2_3` adds a separate panel testing page before the actual/final GUI server is built.

This page is not the final driving GUI and it is not a copy of the older API testing page. It is a flexible layout lab used to test the planned final-GUI panels under different sizes, densities, themes, and viewport environments.

## Run

From inside `PiSD/`:

```bash
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/panel-testing
```

## Planned final-GUI panels listed

The page lists these planned panels:

```text
System Status
Camera Preview
Camera Settings
Motor Settings
Motor Channel Calibration
Manual Drive
Safety Stop
Error Monitor
API Inspector
Validation Checklist
Recording and Dataset
Model and Lane Runtime
```

The last two panels are intentional placeholders. They reserve responsive layout space for later recording/dataset and model/runtime work without pretending those systems are complete yet.

## Style and size settings to test

The left side control column changes CSS variables and layout settings for every panel:

```text
theme: dark / light / high contrast
layout mode: adaptive grid / single column / dense dashboard / wide control desk
viewport preset: auto / phone / tablet / laptop / large monitor
panel size preset: auto / compact / standard / large / stress mixed
density: compact / comfortable / spacious
font scale
panel gap
corner radius
border strength
shadow strength
minimum panel width
preview aspect ratio
```

Use these settings to check whether each panel remains readable and usable on different screens.

## Built-in panel checks

Click:

```text
Run all panel checks
```

Expected output:

```text
OK   PISD-OK-000   panel.summary - failed=0
```

Each panel also has a small `Test` button to check that panel's required structure and size controls are present.

## API and manifest

The page uses:

```text
GET /api/panel-testing/manifest
```

The manifest lists:

- the page route
- planned panel IDs
- panel groups
- style controls
- design rules for flexibility and safety

## Validation script

Run:

```bash
python3 scripts/test_panel_testing_page.py
```

Static-only version, useful away from the Pi or without Flask route checks:

```bash
python3 scripts/test_panel_testing_page.py --static-only
```

Expected lines include:

```text
OK   PISD-OK-000   panel_gui.file.template - pisd/web/templates/panel_testing.html exists
OK   PISD-OK-000   panel_gui.source_contract - panel lab source includes panel registry, style controls, size controls, and responsive rules
OK   PISD-OK-000   panel_gui.route.page - /panel-testing loaded
OK   PISD-OK-000   panel_gui.manifest_contract - panel manifest lists planned final panels and style controls
```

## Safety

The panel testing page includes controls that represent motor and driving panels, but it should not become the final driving interface. Real motor output remains governed by backend safety rules. The STOP route is still:

```text
POST /api/control/stop
```

The motor channel and manual-drive panel shapes are for layout and interaction testing before building the final GUI.
