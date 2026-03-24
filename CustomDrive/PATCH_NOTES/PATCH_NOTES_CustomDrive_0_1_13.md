# PATCH NOTES — CustomDrive 0_1_13

## Request summary
Update the new CustomDrive GUI control page so it matches the current PiServer direction better:
- no mode selection
- live camera preview visible on the main page
- arranged default layout
- style settings as an overlay window, not a separate page
- a right-side manual drag pad
- drag pad wired to the real PiServer motor path

## Why this patch was needed
The previous GUI shell was still too empty for actual driving:
- the preview path was present but the page layout was not yet arranged as a real control workspace
- style settings still lived as a separate page
- manual drive had not been wired into the new GUI shell

## Anti-rollback review performed
Checked the latest accepted CustomDrive GUI direction before patching:
- `0_1_12` fresh PiServer-style GUI shell with live camera and no mode tabs
- `0_1_11` dual-servo test changes
- `0_1_10` first empty PiServer-style GUI shell
- repo `0_1_9` standalone servo test

This patch does **not** remove:
- `run_custom_drive_manual.py`
- servo test tools
- port `5050` default behavior
- the PiServer camera/motor integration path already introduced for live control work

## Files changed
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/README.md`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_13.md`

## Exact behavior changed

### 1. GUI launcher now starts the PiServer-style control page directly
`run_custom_drive_web.py` now loads `custom_drive.gui_control_app` directly and prints clear browser URLs.

### 2. GUI app now uses PiServer control flow, not a placeholder-only shell
`custom_drive/gui_control_app.py` now creates and starts:
- PiServer `CameraService`
- PiServer `MotorService`
- PiServer `ModelService`
- PiServer `RecorderService`
- PiServer `ControlService`
- PiServer algorithm registry

The GUI forces PiServer `manual` mode for this page and sends manual steering/throttle through `ControlService`, so on the Pi it uses the same real motor path as PiServer.

### 3. Live camera now uses a direct MJPEG-style feed route
Added `/video_feed` to the GUI app and switched the page to a direct live image source. This is closer to PiServer and avoids the earlier empty preview feel.

### 4. Default layout arranged as a real control workspace
The new default layout is:
- full-width status strip on top
- large live camera panel on the left
- manual drive panel on the right
- system/debug panel below the drive panel

### 5. Style settings moved into a top overlay window
The separate style page is no longer part of the active GUI flow.
The new GUI opens a PiServer-style overlay modal with theme and spacing controls.

### 6. Right-side manual drag pad added and wired to live control
The page now includes:
- drag pad / joystick area
- max throttle slider
- steer mix slider
- steer bias slider
- center button
- stop drive button
- preview toggle
- E-stop toggle
- save runtime button

The drag pad sends steering and throttle to `/api/control`, which forwards them into PiServer `ControlService` in `manual` mode.

## Root cause / code review findings
The previous GUI shell had been rebuilt as a clean page, but the actual control path had not yet been reattached. That left the page visually closer to the requested direction, but not functionally close enough to PiServer’s real manual-driving behavior.

## Verification actually performed
- merged the latest accepted GUI shell forward before patching
- `python -m compileall CustomDrive`
- reviewed launcher path, Flask app factory path, and PiServer import path

## Known limits / next steps
- keyboard driving is not added yet; this patch focuses on the drag pad
- arm controls are not yet moved into this new GUI shell
- the old unused `settings.html` scaffold may still remain in the folder, but the active GUI no longer depends on it
- real motor output still depends on the Pi having working PiServer runtime dependencies and GPIO access
