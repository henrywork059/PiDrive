# PATCH NOTES — PiSD 0.2.4

## Request summary

Add the next panel-testing patch before the actual GUI server is built. The page should not only list planned panels visually; it should also map every planned final-GUI panel to its safe API contract, allow per-panel testing, show expected/last responses, and support export/import of panel style and size presets.

## Cause / reason

PiSD 0.2.3 introduced a flexible panel testing page, but it was mostly a layout/styling lab. Before building the real GUI server, each planned panel needs a clear contract showing which API endpoints it will use, which tests are safe, which actions are dangerous, and which `PISD-*` code is expected.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/app.py`
- `PiSD/pisd/core/errors.py`
- `PiSD/pisd/core/panel_contracts.py`
- `PiSD/pisd/web/templates/panel_testing.html`
- `PiSD/pisd/web/static/css/panel_testing.css`
- `PiSD/pisd/web/static/js/panel_testing.js`
- `PiSD/scripts/run_standard_validation.py`
- `PiSD/scripts/test_panel_testing_page.py`
- `PiSD/scripts/test_panel_api_contracts.py`
- `PiSD/docs/ERROR_CODES.md`
- `PiSD/docs/PANEL_TESTING_GUI.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/docs/GUI_FUNCTION_SPEC.md`
- `PiSD/README.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_2_4.md`

## Behaviour changed

### Shared panel contract map

Added `pisd/core/panel_contracts.py`, which defines the planned final-GUI panels and their API contract data:

- panel ID
- title and purpose
- group
- planned body type
- default size
- minimum width
- responsive behaviour note
- endpoint list
- safe test action
- expected `PISD-*` code or codes
- dangerous-action flag

### New contract API

Added:

```text
GET /api/panel-testing/contracts
```

The existing `/api/panel-testing/manifest` now includes the same contract details.

### Panel testing page improvements

`/panel-testing` now includes per-panel controls:

- `Test panel`
- `Contract`
- `Last`
- `Expected`

It also includes page-level buttons:

- `Run structure checks`
- `Run panel API checks`
- `Save preset`
- `Load preset`
- `Export preset`
- `Import preset`
- `Export JSON report`

Panel presets are browser-local and do not write to PiSD config files.

### New validation script

Added:

```bash
python3 scripts/test_panel_api_contracts.py
```

This validates panel contract data, manifest/contract routes, and safe panel API actions. It does not arm real motor output.

### New error codes

- `PISD-TEST-013` — intentional skip for future placeholder panels.
- `PISD-TEST-014` — panel API contract, endpoint, expected-code, or safe action validation failed.

## Safety notes

- Real motor output is not armed by the panel API contract tests.
- Motor-channel safe checks accept either `PISD-OK-000` in simulation or `PISD-MOT-008` in real hardware mode when not armed.
- Manual-drive safe checks use zero steering/throttle only.
- Future placeholder panels use `PISD-TEST-013` instead of pretending recording/model runtime is implemented.

## Verification performed

Locally performed in this packaging environment:

- `python3 -m compileall PiSD.py pisd scripts`
- `python3 PiSD.py --status-only`
- `python3 scripts/check_error_reporting.py`
- `python3 scripts/test_panel_testing_page.py --static-only`
- `python3 scripts/test_panel_api_contracts.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`
- patch zip content check for changed/new files only
- checked no duplicate `requirement.txt`
- checked no `__pycache__` or `test_outputs` in patch zip

## Not verified here

- Browser interaction on the Raspberry Pi.
- Full Flask route execution on the Raspberry Pi.
- Real camera or motor hardware, because this environment has no Pi hardware attached.

## Recommended Pi test commands

After applying the patch:

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_panel_testing_page.py
python3 scripts/test_panel_api_contracts.py --hardware
python3 scripts/run_standard_validation.py --hardware --skip-camera --skip-motor
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Open:

```text
http://<pi-ip>:5050/panel-testing
```

Then click:

```text
Run structure checks
Run panel API checks
```

Expected browser summary:

```text
OK   PISD-OK-000   panel.api_summary - failed=0
```

Future placeholder panels may report `SKIP PISD-TEST-013`, which is acceptable at this stage.
