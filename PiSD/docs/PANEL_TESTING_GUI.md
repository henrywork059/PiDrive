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

---

## PiSD 0.2.4 panel API contract testing

`PiSD_0_2_4` expands the panel testing page from a visual/layout lab into a visual plus API-contract lab.

Each planned final-GUI panel now has a contract containing:

```text
panel id
title
group
purpose
required endpoints
safe test action
expected PISD code or codes
dangerous-action flag
minimum panel width
responsive behaviour note
```

The panel page now provides these actions on each panel:

```text
Test panel       checks panel structure and runs its safe API action
Contract         shows the declared API contract
Last             shows the latest response from that panel's safe API test
Expected         shows the expected endpoint and PISD code
```

The page-level buttons are:

```text
Run structure checks     checks panel DOM, size controls, and contract presence
Run panel API checks     runs every safe panel API contract test
Save preset              saves the current panel style/size settings to browser localStorage
Load preset              reloads the browser-saved preset
Export preset            downloads a JSON preset
Import preset            imports a JSON preset
Export JSON report       downloads the current test report
```

Safe panel API checks do not arm real motor output. The motor-channel panel accepts either:

```text
PISD-OK-000   simulation-safe result
PISD-MOT-008  real-hardware safety refusal when not armed
```

Future placeholder panels use:

```text
PISD-TEST-013
```

Contract failures use:

```text
PISD-TEST-014
```

## API contract endpoints

```text
GET /api/panel-testing/manifest
GET /api/panel-testing/contracts
```

## New validation script

Run:

```bash
python3 scripts/test_panel_api_contracts.py
```

Hardware-mode contract test without arming motors:

```bash
python3 scripts/test_panel_api_contracts.py --hardware
```

Static/contract-data only:

```bash
python3 scripts/test_panel_api_contracts.py --static-only
```

Example successful output:

```text
OK   PISD-OK-000   panel_contract.registry - 12 panel contracts declared
OK   PISD-OK-000   panel_contract.fields - all panel contracts include required fields
OK   PISD-OK-000   panel_contract.manifest_route - manifest route includes panel API contracts
OK   PISD-OK-000   panel.system_status.api - safe action returned expected code via HTTP 200
SKIP PISD-TEST-013 panel.recording.placeholder - future placeholder intentionally skipped
```
