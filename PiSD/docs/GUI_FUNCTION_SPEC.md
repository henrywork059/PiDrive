# PiSD GUI and Function Specification Draft

## Current main dashboard shell

`PiSD_0_2_5` starts the actual GUI server shell. The root route `/` now renders a front page mode selector, while the development/testing pages remain separate:

```text
/               actual main dashboard shell
/testing        API and settings testing server page
/panel-testing  panel layout and API-contract testing lab
```

The first dashboard shell includes:

- System Status
- Camera Preview
- Manual Drive
- Motor Channel Calibration
- Safety Stop
- Error Monitor
- Action Log

Safety rule: manual drive and motor channel calibration are locked by default and only enable after the page safety checkbox is ticked. STOP controls remain available at all times.

Focused validation:

```bash
python3 scripts/test_main_dashboard.py
```

## Testing server GUI

`PiSD_0_2_1` provided a temporary testing server GUI. Since `PiSD_0_2_5`, the temporary tester lives at `/testing` only.

This page is intentionally not the final driving UI. It is a browser-based API and settings tester for checking backend service behaviour before the actual PiServer-style GUI is extended.

It includes:

- camera preview and camera service buttons
- camera settings apply form
- motor settings apply form
- one-by-one motor channel test panel
- custom API caller
- safe browser smoke-test button
- status / last response / error-code panels
- emergency stop button

## Current API endpoints

```text
GET  /api/test-gui/manifest
GET  /api/status
GET  /api/errors
POST /api/errors/clear
POST /api/camera/start
POST /api/camera/stop
GET  /api/camera/config
GET  /api/camera/capabilities
POST /api/camera/apply
GET  /api/camera/frame.jpg
GET  /video_feed
GET  /api/motor/config
POST /api/motor/apply
POST /api/motor/test-channel
POST /api/control/manual
POST /api/control/stop
GET  /api/panel-testing/manifest
GET  /api/panel-testing/contracts
```

## Design goals

- fast loading
- clear control state
- safe default simulation mode
- obvious emergency stop
- no hidden backend failures
- all controls call real APIs
- every panel action shows a `PISD-*` code
- testing pages remain available while the actual dashboard evolves

## Main dashboard v1 panels

### System Status

Displays PiSD version, hardware/simulation state, camera backend, motor adapter, and raw status JSON.

### Camera Preview

Starts/stops the camera and refreshes `/api/camera/frame.jpg`. The trusted visual path remains `capture_source=request`; the confirmed array/CV path remains `array_color_order=rgb`.

### Manual Drive

Provides simple bench controls for forward, reverse, left, right, and STOP. Movement buttons are disabled until the safety checkbox is selected.

### Motor Channel Calibration

Tests one side at a time using `/api/motor/test-channel`. Direction is not fixed here because final direction mapping will be controlled by future GUI settings.

### Safety Stop

Always available. Calls `/api/control/stop`.

### Error Monitor

Reads and clears error history through `/api/errors` and `/api/errors/clear`.

### Action Log

Shows the most recent API action, HTTP status, response JSON, and `PISD-*` code.

## Panel testing page added in PiSD 0.2.3

`/panel-testing` is a panel layout lab before the actual GUI server is fully built. It does not copy the old testing-server cards. It rebuilds the planned final-GUI panels as flexible, responsive test components.

Panels currently listed for final GUI planning:

- System Status
- Camera Preview
- Camera Settings
- Motor Settings
- Motor Channel Calibration
- Manual Drive
- Safety Stop
- Error Monitor
- API Inspector
- Validation Checklist
- Recording and Dataset
- Model and Lane Runtime

The panel lab includes environment and style controls for:

- theme
- layout mode
- viewport preset
- panel size preset
- density
- font scale
- panel gap
- corner radius
- border and shadow strength
- minimum panel width
- preview aspect ratio

Use this page to decide which panel sizes, densities, and layout behaviour are safe before expanding the final dashboard.

## PiSD 0.2.4 panel API contract rule

Before a planned final-GUI panel is implemented, it should have a declared contract in:

```text
PiSD/pisd/core/panel_contracts.py
```

Each contract should define:

```text
id
title
group
purpose
body/default size
minimum width
responsive behaviour
endpoint list
safe test action
expected PISD code(s)
dangerous_action flag
```

The final GUI should not directly add a new control panel without first adding or updating this panel contract and passing:

```bash
python3 scripts/test_panel_api_contracts.py
python3 scripts/test_panel_testing_page.py
```

Motor or drive panels must treat real movement as dangerous. Safe API tests may only use zero-output commands or unarmed checks that return `PISD-MOT-008` on hardware.

## Later GUI work

Do not add these until the dashboard shell is proven:

- draggable/resizable panels
- layout persistence
- dataset recording
- model/lane runtime integration
- theme editor beyond panel-testing presets
- training integration


## PiSD 0.2.6 route model

The GUI is now split by mode before the final server UI is built:

- `/` is the front page and mode selector.
- `/settings` is the settings tab for camera/motor configuration API calls.
- `/testing` is the testing tab for broader API and settings checks.
- `/dashboard` preserves the actual dashboard shell from 0.2.5.
- `/panel-testing` preserves the panel layout/API contract lab.

All tabs/pages include a **Back to Front Page** link.

## Live preview FPS direction

The GUI should use `/video_feed` for live preview. `/api/camera/frame.jpg` remains available for snapshots, smoke tests, and single-frame API checks.

The camera status now reports these live-frame metrics:

- `target_fps`
- `measured_capture_fps`
- `last_capture_loop_ms`
- `average_capture_loop_ms`
- `last_encode_ms`
- `average_encode_ms`
- `last_frame_bytes`
- `frames_dropped_or_empty`

The testing GUI exposes these through `/api/camera/fps-stats` and the **Live FPS pipeline test** panel.

## 0.2.8 compact front page and panel presentation settings

The root route `/` remains the compact front page/mode selector. Pages should not include cross-tab switching buttons; users choose pages from the front page. Individual pages may keep only a `Back to Front Page` link plus local actions such as refresh or STOP.

A new `/panel-presentation` page controls shared presentation settings for panels. It is separate from `/panel-testing`.

`/panel-presentation` saves browser-local settings for:

- theme
- layout mode
- density
- font scale
- panel gap
- panel radius
- border and shadow strength
- minimum panel width
- preview aspect ratio

The shared presentation CSS/JS is loaded by the front page, settings tab, testing tab, dashboard, and panel testing page.

## 0.2.9 Manual Drive tab and shared settings behaviour

The front page now exposes a dedicated `/manual-drive` page for easy user control.
This is different from `/dashboard`, which remains the broader dashboard shell.

Manual Drive page panels:

- Camera Preview: simple live view using `/video_feed`.
- Running Status: important hardware/camera/motor status only.
- Manual Pad: forward, reverse, left, right, and STOP controls.
- Safety Stop: large STOP button that remains active even when motor movement is locked.
- Response: last API response and PISD code.

Safety requirements:

- Movement buttons are disabled by default.
- User must enable the safety checkbox before drive commands can be sent.
- STOP must always remain active.
- Any lock/refusal should show `PISD-MOT-008` or another relevant `PISD-*` code.

Settings behaviour:

- `/settings` saves camera/motor form values in browser localStorage.
- `/settings` applies runtime changes through `/api/camera/apply` and `/api/motor/apply`.
- Applied runtime settings affect all pages because all tabs share the same backend services.
- `/panel-presentation` saves browser-local panel presentation settings and applies them across all GUI pages, including `/manual-drive`.

Panel presentation controls now include panel padding, panel header mode, button size, console height, preview fit, and card accent strength in addition to the original density/layout/theme controls.
