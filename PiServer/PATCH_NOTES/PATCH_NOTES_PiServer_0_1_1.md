# PATCH NOTES — PiServer 0_1_1

## Goal

Add clearer mode switching in the web GUI so Manual, Lane Detection, and Full Auto feel like distinct working modes, and add a settings tab that follows the selected mode.

## User request addressed

- Add tab function to differentiate different modes
- Manual, Full Auto, Lane Detection should be separate selectable tabs
- Add a settings tab for each mode
- The settings tab should only show the settings for the selected mode

## Root issue

PiServer 0_1_0 already had page tabs, but they were still generic workspace pages and did not behave like real driving modes.

Problems in 0_1_0:

1. Top tabs were still closer to workspace views than mode selectors.
2. Runtime behavior was not strongly tied to the selected tab.
3. The settings area was shared and did not feel mode-specific.
4. Manual / lane-assisted / full-auto workflows were not clearly separated in presentation.

## Final changes made

### 1) True mode tabs added

The top bar now uses:

- Manual
- Lane Detection
- Full Auto

Selecting a tab now calls a dedicated backend mode endpoint and switches the runtime mode directly.

### 2) Mode-to-algorithm mapping added in backend

Added mode mapping in `ControlService`:

- `manual -> manual`
- `lane -> auto_steer`
- `full_auto -> autopilot`

This means the selected tab now drives the actual control mode, not just the page label.

### 3) Per-mode runtime profiles added

Added mode-specific runtime profiles in state/config for:

- `max_throttle`
- `steer_mix`

Each mode now keeps its own tuning values instead of one shared pair of settings for every workflow.

### 4) Mode workspace panel redesigned

The old “Drive + algorithm” panel was replaced with a clearer “Mode workspace” panel.

It now has:

- `Overview` sub-tab
- dynamic mode-specific `Settings` sub-tab

The Settings tab title changes with the current mode, for example:

- `Manual Settings`
- `Lane Detection Settings`
- `Full Auto Settings`

### 5) Mode-specific settings visibility added

The settings content now changes with the selected mode.

Examples:

- Manual mode shows direct-drive wording and hides model tools
- Lane Detection shows model tools and lane-specific wording
- Full Auto shows model tools and explains the joystick lock behavior

### 6) Manual control panel behavior updated

The joystick panel now changes its title and instructions by mode:

- Manual: normal joystick driving
- Lane Detection: joystick controls throttle while model steers
- Full Auto: joystick pad is visually locked, Stop/E-Stop still available

### 7) Legacy compatibility handled

Older saved values like:

- `training`
- `auto`
- `lane_detection`

are normalized into the new mode names so older saved configs do not break the UI.

## Files changed

- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/algorithms/auto_steer.py`
- `PiServer/piserver/algorithms/autopilot.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/config/runtime.json`
- `PiServer/README.md`

## Verification completed

### Verified in container

- Python files compile successfully with `py_compile`
- Project zip rebuilt successfully

### Not fully runtime-verified in container

- Flask was not installed in this container, so I could not fully launch the web server here
- Browser interaction for the new UI tabs was not end-to-end tested in the container

## Result

PiServer now behaves much closer to a real mode-driven control app:

- the top tabs act as actual runtime modes
- the settings tab follows the selected mode
- mode tuning is separated per mode
- the manual panel instructions and behavior now match the selected driving mode

## Suggested next improvement

A good next step would be adding separate mode pages for:

- shared controls
- advanced model settings
- lane visualization settings
- full-auto safety limits / fallback rules

That would make the GUI even closer to your trainer app structure while still staying browser-friendly.
