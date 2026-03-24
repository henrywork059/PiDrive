# PATCH NOTES — CustomDrive 0_1_15

## Request summary
Split the top-right GUI controls into two separate buttons:
- **Style Settings**
- **Drive Settings**

Keep the current responsive layout, keep the live camera, and keep the drag pad connected to the real PiServer motor path.

## Why this patch was needed
The previous GUI refinement (`0_1_14`) moved both appearance controls and drive tuning into one shared overlay. That saved space on the main page, but it still mixed two different groups of settings into one entry point.

This patch separates them without changing the active control layout or the existing camera/motor integration.

## Anti-rollback review performed
Checked the latest accepted GUI direction before patching:
- `0_1_14` responsive single-page GUI with live camera, drag pad, and one shared settings overlay
- `0_1_13` PiServer-style overlay, live camera, and real motor drag pad path
- `0_1_12` clean GUI shell with no mode tabs and live camera scaffold

This patch keeps:
- the single-page GUI layout
- the live camera panel on the main page
- the responsive workspace sizing changes from `0_1_14`
- the drag pad posting to the real PiServer motor path
- the `run_custom_drive_gui.py` / `run_custom_drive_web.py` launcher flow

## Files changed
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_15.md`

## Exact behavior changed

### 1. Two separate top-right buttons
The shared **Settings** button was replaced with two buttons:
- **Drive Settings**
- **Style Settings**

### 2. Drive settings now open in their own window
Drive tuning controls now open in a dedicated overlay window containing:
- max throttle
- steer mix
- steer bias
- save drive button

### 3. Style settings now open in their own window
Appearance controls now open in a separate overlay window containing:
- color controls
- font size
- spacing
- panel radius
- reset style
- save style

### 4. Existing responsive layout kept intact
This patch does not change the workspace grid, camera panel placement, or drag pad placement introduced in the earlier GUI updates.

## Root cause / code review findings
The previous combined overlay was functionally correct but was mixing two unrelated setting groups into one modal workflow. Splitting the modal entry points is a lower-risk UI change than reshaping the page again, and it keeps the current motor/control behavior untouched.

## Verification actually performed
- Applied the patch forward on top of the latest accepted GUI state
- Ran `python -m compileall CustomDrive`
- Checked that the updated GUI JS now binds:
  - `openDriveSettingsBtn`
  - `openStyleSettingsBtn`
  - separate modal close behavior for both overlays

## Known limits / next steps
- This patch does not add new controls to the main page
- It does not change arm control integration
- Full browser/runtime verification still depends on the Pi environment
