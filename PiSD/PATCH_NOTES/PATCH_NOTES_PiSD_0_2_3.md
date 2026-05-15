# PATCH NOTES - PiSD 0.2.3

## Request summary

User requested a GUI panel testing page before the actual main GUI server is built.

User also clarified:

- panels should be remade rather than copied from old testing GUI panels
- panels should be flexible and adaptable to different environments and settings
- the page should list every panel planned for the actual GUI
- the page should include panel style and size settings so each panel can be tested under different conditions

## Cause / context

`PiSD_0_2_1` and `PiSD_0_2_2` added and hardened the temporary API/settings testing GUI. That page is useful for checking service calls, but it is not a good place to decide the final GUI panel design.

Before building the real server GUI, PiSD needs a separate layout lab where planned panels can be tested for:

- small phone/tablet/laptop/large monitor widths
- compact/standard/large/mixed panel sizes
- density changes
- style changes
- readable status/error-code display
- future panel placement without pretending unfinished features already exist

## Files changed

Changed:

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/README.md`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/docs/TESTING_SERVER_GUI.md`
- `PiSD/docs/TEST_PLAN.md`

Added:

- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/pisd/web/static/css/panel_testing.css`
- `PiSD/pisd/web/static/js/panel_testing.js`
- `PiSD/scripts/test_panel_testing_page.py`
- `PiSD/docs/PANEL_TESTING_GUI.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_3.md`

## Behaviour changed

### New panel testing page

Added:

```text
GET /panel-testing
```

This page is separate from the API/settings testing page at `/` and `/testing`.

It lists the planned actual-GUI panels:

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

The final two are intentionally marked as future placeholders so layout space can be tested without falsely claiming recording/model runtime functionality is complete.

### New panel manifest endpoint

Added:

```text
GET /api/panel-testing/manifest
```

The manifest lists:

- page route
- panel IDs
- panel titles
- panel groups
- panel purposes
- design rules
- supported style controls

### Flexible/adaptable panel lab

The page includes controls for:

```text
theme
layout mode
viewport preset
panel size preset
density
font scale
panel gap
corner radius
border strength
shadow strength
minimum panel width
preview aspect ratio
```

The panels use responsive CSS grid, CSS variables, container queries, and mobile media rules so behaviour can be tested across environments before final GUI design.

### Built-in browser panel checks

Added a `Run all panel checks` button. It verifies the panel registry and each panel's expected structure/size controls in the browser and prints simple `OK` / `FAIL` lines.

Expected successful summary:

```text
OK   PISD-OK-000   panel.summary - failed=0
```

### Validation script

Added:

```bash
python3 scripts/test_panel_testing_page.py
```

This prints simple `OK` / `FAIL` lines with PiSD error codes and writes:

```text
test_outputs/panel_testing_gui/summary.json
```

Static-only mode:

```bash
python3 scripts/test_panel_testing_page.py --static-only
```

### Standard validation expanded

`run_standard_validation.py` now also checks the panel testing GUI unless `--skip-gui` is used.

It checks:

- `panel_testing.html` exists
- `panel_testing.css` exists
- `panel_testing.js` exists
- panel source includes required panel IDs
- style/size controls exist
- responsive CSS tokens exist
- `/panel-testing` route loads
- panel static CSS/JS routes load
- `/api/panel-testing/manifest` includes required panels and style controls

## Error reporting

Added:

```text
PISD-TEST-012
```

Meaning: panel testing GUI page/static/manifest/source contract failed validation.

## Safety behaviour

No change to hardware safety.

Real motor output remains controlled by existing backend rules. The new page is for panel layout and interaction testing, not final driving.

`POST /api/control/stop` remains the STOP route used by the page.

## Verification actually performed

Performed locally in the packaging environment:

- `python3 -m py_compile PiSD.py pisd/app.py pisd/core/*.py pisd/services/*.py scripts/*.py`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_panel_testing_page.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`
- patch-only zip structure check
- confirmed no `__pycache__` folders are included
- confirmed no `test_outputs` are included
- confirmed no duplicate `requirement.txt` was restored

## Not verified here

- Full Flask route execution, because Flask is not installed in this packaging environment.
- Browser rendering on the Raspberry Pi screen.
- Real Raspberry Pi camera hardware.
- Real GPIO/motor output.

Run this on the Pi after applying the patch:

```bash
python3 scripts/test_panel_testing_page.py
python3 scripts/run_standard_validation.py --hardware
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then open:

```text
http://<pi-ip>:5050/panel-testing
```

## Known limits / next steps

- This is still not the final main GUI.
- The panel lab tests layout, component structure, size modes, and style adaptability.
- Persistent settings are not added in this patch.
- Recording/dataset and model/runtime panels remain planned placeholders only.
- After user testing, the next patch can either refine the panel lab or start building the actual main GUI using the tested panel structure.
