# PATCH NOTES — PiSD_0_0_0

## Request summary

Create a new clean path `PiDrive/PiSD` to go back to square one for developing and testing the PiServer GUI and functions.

The requested starter package should include:

- documentation
- possible package requirement file
- `PiSD.py` placeholder as the main code

## Cause / reason for this new component

The existing PiServer has accumulated working runtime behavior, UI changes, configuration behavior, and hardware-specific code. A separate PiSD folder gives a safe place to rebuild and test the next design without accidentally rolling back current PiServer behavior.

## Files added

```text
PiSD/PiSD.py
PiSD/README.md
PiSD/requirement.txt
PiSD/requirements.txt
PiSD/docs/ARCHITECTURE.md
PiSD/docs/DEVELOPMENT_PLAN.md
PiSD/docs/GUI_FUNCTION_SPEC.md
PiSD/docs/TEST_PLAN.md
PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_0_0.md
```

## Behavior added

- Adds a clean new PiSD component folder.
- Adds a placeholder Python launcher.
- The launcher can print JSON status with `python PiSD.py --status-only`.
- If Flask is installed, the launcher starts a small placeholder web page and `/api/status` endpoint.
- The placeholder avoids direct Raspberry Pi hardware imports, so it can be tested on PC first.

## Compatibility notes

- Existing `PiServer/` files are not modified.
- Existing runtime/config files are not modified.
- PiSD is not yet a replacement for PiServer.
- `requirement.txt` is included because it was requested.
- `requirements.txt` is also included as a standard pip-compatible alias with the same contents.

## Verification actually performed

Performed locally in this workspace:

- Confirmed the uploaded repo archive does not already contain a top-level `PiSD/` folder.
- Ran Python compilation check on `PiSD/PiSD.py`.
- Ran `python PiSD.py --status-only` and confirmed it returns placeholder JSON.
- Checked the final zip listing to confirm it only contains the new `PiSD/` folder and expected files.

## Known limits / next steps

- No real PiServer GUI has been implemented yet.
- No real camera, motor, model, or recorder service has been implemented yet.
- Next recommended patch: add a real web UI shell, static assets, status polling, and a simulated runtime state service.
