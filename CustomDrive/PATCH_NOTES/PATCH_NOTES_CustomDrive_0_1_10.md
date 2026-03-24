# PATCH NOTES — CustomDrive 0_1_10

## Request summary
Replace the old CustomDrive browser page with a **new empty GUI control web** that follows the current **PiServer** style and coding direction.

The goal of this patch is not to restore the old runtime-heavy monitor. It is to create a clean, reliable GUI control base first.

## Why this patch was needed
The previous CustomDrive web path had grown into a mixed runtime/monitor page and was no longer the right starting point for the new GUI direction.

To avoid carrying forward layout and startup problems, this patch makes the GUI control page light and intentional:
- same launcher path (`run_custom_drive_gui.py` / `run_custom_drive_web.py`)
- PiServer-like app-factory structure
- PiServer-like top bar, panels, theme handling, and settings flow
- empty placeholder panels instead of half-wired controls

## Files changed
- `CustomDrive/custom_drive/gui_control_state.py`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/templates/settings.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/theme.js`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/settings.js`
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/README.md`

## Exact behavior changed
- `run_custom_drive_gui.py` still launches the browser GUI path.
- That GUI path now opens a **new empty GUI control shell** instead of the older runtime-heavy CustomDrive web page.
- The new shell uses:
  - Flask app-factory pattern
  - `app.config["services"]` storage
  - PiServer-style panel structure
  - PiServer-style static theme variables
  - a separate `/settings` page for style controls
- The new page includes:
  - top bar
  - page tabs
  - full-width status strip
  - empty viewer panel
  - empty drive-control panel
  - empty system/debug panel
  - empty settings panel

## Cause / root cause
The older GUI path mixed runtime startup and browser UI too early. That made it harder to reuse as a clean GUI control base.

## Verification actually performed
- `python -m compileall CustomDrive`
- launched structure inspection against the uploaded `PiDrive-main.zip`
- checked launcher import path points to the new GUI app

## Known limits / next steps
- This patch intentionally does **not** wire back real drive controls yet.
- This patch intentionally does **not** boot the older mission runtime in the GUI.
- Next patches can now add panels back one at a time using this new shell as the base.
