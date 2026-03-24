# PATCH NOTES — CustomDrive 0_1_14

## Request summary
Refine the new GUI control page again so the default layout stays inside the visible browser window, remove the drive tuning sliders from the main page, and move those settings into a top-right settings overlay. Keep the live camera visible and keep the drag pad connected to the real PiServer motor path.

## Why this patch was needed
The previous GUI direction was correct, but the default layout could still overflow smaller browser windows and some control tuning sliders were still occupying space in the main drive panel. That made the page feel less like the latest PiServer direction.

## Anti-rollback review performed
Checked the latest accepted GUI updates before patching:
- `0_1_13` single-page GUI control shell with live camera, drag pad, overlay settings, and PiServer motor path
- `0_1_12` new PiServer-style GUI shell with live camera and no mode tabs
- `0_1_11` dual-servo test update
- `0_1_10` standalone dual-servo tester / earlier GUI-shell direction

This patch keeps:
- `run_custom_drive_gui.py` and `run_custom_drive_web.py` as the GUI launch path
- PiServer `CameraService`, `MotorService`, and `ControlService` integration
- the live camera feed route
- the right-side drag pad and real motor control flow

## Files changed
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_14.md`

## Exact behavior changed

### 1. Default layout now fits the window more reliably
- Reworked the GUI grid to use explicit grid areas instead of the earlier looser row spanning.
- Changed the page to use flex-based full-height layout with `100dvh` handling so the workspace resizes with the visible browser window more reliably.
- Added more responsive breakpoints so panels stack cleanly on narrower or shorter windows instead of spilling outside the page.

### 2. Main drive panel is simpler
- Removed the always-visible sliders for:
  - max throttle
  - steer mix
  - steer bias
- Kept the drag pad, readout, and direct drive actions in the main panel.

### 3. Top-right settings button now owns those controls
- Replaced the top-right style-only button with a general **Settings** button.
- The overlay now contains:
  - drive tuning sliders for max throttle, steer mix, and steer bias
  - PiServer-style appearance controls in the same window
- The drive settings save button now lives inside that overlay.

### 4. Live camera preview kept as the main left panel
- The main page still opens with the live camera visible.
- Added a client-side preview error message so camera failures are easier to notice and debug.

## Root cause / code review findings
- The earlier layout depended on fixed row structure plus a spanning viewer panel, which could still become awkward on smaller viewport heights.
- The extra runtime sliders on the main drive panel were using valuable space and contributed to the cramped layout.

## Verification actually performed
- Applied the patch forward on top of the latest accepted GUI-shell direction.
- Ran `python -m compileall CustomDrive` successfully.
- Manually reviewed the updated HTML/CSS/JS flow to confirm:
  - no mode switching UI was reintroduced
  - the drag pad control path still posts to `/api/control`
  - the settings overlay now owns the drive tuning sliders

## Known limits / next steps
- This patch does not yet add arm controls into the new GUI shell.
- Full live preview and real motor verification still require the Pi runtime environment.
- Keyboard driving is still not included in this new GUI shell.
