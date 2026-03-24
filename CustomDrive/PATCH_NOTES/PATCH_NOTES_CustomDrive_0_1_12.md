# PATCH NOTES — CustomDrive 0_1_12

## Request summary
Rebuild the CustomDrive GUI as a fresh PiServer-style web shell, remove all mode-selection tabs, and put the live camera on the main page.

## Why this patch
The existing `run_custom_drive_gui.py` entrypoint still launched the older runtime-monitor page. That page carried over mode-related state and a heavier startup path, which was not the clean GUI-control base requested.

## Anti-rollback review performed
Checked the latest current CustomDrive patch notes in the uploaded repo before patching:
- `0_1_9` standalone servo test
- `0_1_8` default-enabled arm + press/hold lift behavior
- `0_1_7` PiServer-style manual page cleanup
- `0_1_6` default port alignment to `5050`

This patch does **not** remove:
- manual-control app on `run_custom_drive_manual.py`
- servo test tools
- port `5050` default behavior

Instead, it only changes the **GUI launcher path** so `run_custom_drive_gui.py` opens the new GUI shell.

## Files changed
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/README.md`
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/templates/settings.html`
- `CustomDrive/custom_drive/gui_web/static/theme.js`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/settings.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_12.md`

## Exact behavior changed

### 1. New PiServer-style GUI app-factory
Added `custom_drive/gui_control_app.py`.

It follows the same broad pattern as PiServer:
- Flask app factory
- `app.config["services"]`
- direct use of PiServer `ConfigStore`
- direct use of PiServer `CameraService`
- explicit cleanup with `atexit`
- lightweight JSON status endpoint
- polled JPEG frame endpoint

### 2. Mode-selection tabs removed
The new GUI has **no page tabs** and **no mode switching**.

It always opens as one GUI-control workspace.

### 3. Live camera added to the main page
The new index page includes a large live camera viewer driven by:
- `/api/camera/frame.jpg`
- PiServer `CameraService`

This keeps the camera path easy to manage because it reuses PiServer code directly.

### 4. PiServer-style theme/settings structure added
The new GUI uses:
- `theme.js` copied from the current PiServer theme system
- PiServer-style CSS as the base
- a separate `/settings` page for style tuning
- custom style overrides saved in browser local storage, like PiServer

### 5. GUI launcher redirected to the new shell
`run_custom_drive_web.py` now imports the new GUI app instead of the older `web_app.py` monitor page.

## Verification actually performed
- Built patch against the uploaded `PiDrive-main.zip` tree
- `python -m compileall CustomDrive`
- reviewed the new launcher/import path after patching

## Known limits / next steps
- Drive controls are still placeholders in this new GUI shell
- System/debug panel is still a placeholder
- This patch does not wire manual drive, arm control, or autonomous runtime into the new GUI yet
- Live camera still depends on the Pi having the same camera/runtime dependencies PiServer expects
