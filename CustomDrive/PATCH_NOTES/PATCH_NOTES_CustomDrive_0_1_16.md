# PATCH NOTES — CustomDrive 0_1_16

## Request summary
Build forward from the current CustomDrive state and replace the older GUI path with a fresh PiServer-style GUI control web. Also add:

- live camera preview
- responsive default layout that stays within the browser viewport more reliably
- split top-right buttons for **Drive Settings** and **Style Settings**
- manual drag pad wired to the real PiServer motor/control path
- left-side arm panel with **Up / Down / Open / Close**
- hold-to-move lift motion at **1 degree every 0.1 seconds**
- drive settings for motor direction and turn direction like PiServer
- remove the center stop-drive button from the GUI

## Root cause / why this patch was needed
The uploaded repo still had two separate web directions:

1. `run_custom_drive_gui.py` still launched the older mission-monitor style app in `custom_drive/web_app.py`
2. PiServer-like manual-control logic existed separately, but not as the main GUI path

That mismatch made the GUI hard to evolve and caused newer UI requests to stack on top of the wrong web entrypoint.

## Files changed

### New
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/styles.css`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/gui_web/static/theme.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_16.md`

### Updated
- `CustomDrive/custom_drive/arm_service.py`
- `CustomDrive/custom_drive/manual_control_config.py`
- `CustomDrive/config/manual_control.json`
- `CustomDrive/run_custom_drive_web.py`
- `CustomDrive/README.md`

## Exact behavior changed

### 1. GUI entrypoint now launches a new PiServer-style control app
`run_custom_drive_gui.py` still works, but `run_custom_drive_web.py` now boots a fresh GUI control app instead of the older mission-monitor page.

### 2. New responsive default layout
The GUI now uses a fixed single-page control layout with:

- top status strip
- left arm panel
- center live camera panel
- right manual-drive panel
- lower system panel

The CSS uses breakpoint-based grid changes so panels stay inside the browser window more reliably on smaller screens.

### 3. Live camera preview added to the new GUI
The camera panel now uses PiServer `CameraService` directly and streams from `/video_feed`.

### 4. Drag pad now drives the real motor path
The drag pad and keyboard controls now post to PiServer `ControlService` in `manual` mode using the real motor path already used by PiServer.

### 5. Center stop-drive button removed
The GUI no longer shows the old center stop-drive button. Releasing the drag pad or drive hold buttons returns steering/throttle to zero.

### 6. Drive settings overlay added
A dedicated **Drive Settings** overlay was added for:

- max throttle
- steer mix
- steer bias
- left/right motor direction
- steering direction
- left/right max speed
- left/right bias

These are applied using PiServer-like `/api/motor/apply` and `/api/control` flow and saved back into `PiServer/config/runtime.json`.

### 7. Style settings overlay added
A dedicated **Style Settings** overlay was added. It uses the same PiServer theme-variable approach and local browser storage pattern.

### 8. Arm service made safer and more practical for the real lift
The arm service now supports:

- primary lift servo
- optional secondary lift servo
- configurable secondary multiplier
- configurable lift step interval

The default lift behavior was updated to support the now-tested dual-servo lift path more cleanly.

### 9. Lift hold motion changed to 1° every 0.1s
`Up` and `Down` use hold-to-move logic at 1 degree every 0.1 seconds.

## Config changes
`CustomDrive/config/manual_control.json` and the config normalizer were updated with arm fields for:

- `lift_channel_secondary`
- `lift_secondary_enabled`
- `lift_secondary_multiplier`
- `lift_step_interval_s`

The default grip channel was moved away from the secondary lift channel to avoid obvious overlap in the default config.

## Verification actually performed
- reviewed current `CustomDrive` files and existing patch notes before patching
- checked current PiServer app/routes and current PiServer web patterns before reusing them
- `python -m compileall CustomDrive`

## Known limits / next steps
- real gripper open/close still depends on your actual configured `grip_channel` and angles
- final arm channel mapping may still need one more Pi-side tune after your exact hardware layout is confirmed
- if you want full PiServer-style draggable/resizable docking later, that should be added as a later patch on top of this new GUI shell rather than mixed into this stabilization patch
