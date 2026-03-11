# PATCH NOTES — PiServer 0.1.0

## Goal of this patch

Convert the earlier fixed-script PiCar web backend into a cleaner baseline named **PiServer** so the Pi can:

- boot into a persistent server
- keep the web UI available while the Pi is on
- switch algorithms during runtime
- save/reload runtime settings
- support safer update/restart actions from the web
- use a better-looking dock-style browser UI

## Main problems in the earlier structure

1. Control flow was too predetermined by one script path.
2. Autopilot logic only stepped when `/api/status` was polled, so runtime behavior depended on the browser.
3. Camera, model, recording, motor, and UI logic were coupled tightly.
4. Web presentation was functional but harder to scale and maintain.
5. There was no cleaner baseline for “start on boot and control from browser”.
6. Runtime function changes were limited because algorithm selection was not a first-class module system.

## Architecture changes

### 1) Modular project structure

Added a modular package layout:

- `piserver/core`
- `piserver/algorithms`
- `piserver/services`
- `piserver/web`

This makes future edits easier because each concern has a clearer file location.

### 2) Background control loop

Added `ControlService` as a persistent runtime loop.

Instead of tying automatic behavior to the status endpoint, the control loop now:

- runs continuously
- reads the selected algorithm
- computes steering/throttle
- updates motor output
- records frames when enabled

This is the key change that makes mid-run switching practical.

### 3) Runtime algorithm registry

Added pluggable algorithms:

- `manual`
- `auto_steer`
- `autopilot`
- `stop`

The selected algorithm can now be changed from the web UI at runtime.

### 4) Runtime config persistence

Added `config/runtime.json` and `ConfigStore`.

Runtime settings now support save/reload for:
- active algorithm
- max throttle
- steer mix
- current page

### 5) Camera service fallback design

Added `CameraService` with multiple runtime paths:

- `picamera2` on supported Pi systems
- OpenCV webcam fallback
- generated placeholder frame fallback

This makes development and debugging easier outside the full Pi hardware environment.

### 6) Improved recorder metadata

Recorder now stores:
- `frame_id`
- `session`
- `mode`
- `camera_width`
- `camera_height`
- `camera_format`

Also changed image naming to timestamp-based names so files sort naturally and do not repeat between sessions.

### 7) Safer system actions

Added system endpoints for:
- save config
- reload config
- Git pull
- service restart
- emergency stop

Update/restart is blocked unless:
- recording is off
- throttle is zero
- E-stop is enabled

### 8) Dock-style web workspace

Replaced the earlier simpler panel UI with a more structured workspace:

- top toolbar
- Manual / Training / Auto page tabs
- draggable panels on large screens
- resizable panels on large screens
- saved layout in browser local storage
- responsive stacked layout on smaller screens

## Files added

- `PiServer/server.py`
- `PiServer/README.md`
- `PiServer/requirements.txt`
- `PiServer/config/runtime.json`
- `PiServer/boot/pi_server.service`
- `PiServer/piserver/app.py`
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/core/config_store.py`
- `PiServer/piserver/algorithms/base.py`
- `PiServer/piserver/algorithms/manual.py`
- `PiServer/piserver/algorithms/auto_steer.py`
- `PiServer/piserver/algorithms/autopilot.py`
- `PiServer/piserver/algorithms/stop.py`
- `PiServer/piserver/algorithms/__init__.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/services/recorder_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/update_service.py`
- `PiServer/piserver/services/__init__.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/piserver/web/static/app.js`

## Verification performed

1. Checked Python module syntax with `compileall`.
2. Reviewed that the new server wiring points to the modular services.
3. Verified the zip contains:
   - full `PiServer/` project
   - `PATCH_NOTES/` folder
4. Verified that runtime config, boot service, and web assets are included.

## Notes for next improvement round

Good next steps after this baseline:

1. Add session download / delete endpoints.
2. Add branch/tag selector for Git update.
3. Add per-page panel visibility presets.
4. Add optional websocket status streaming.
5. Add authentication if the UI will ever leave a trusted LAN.
6. Add more algorithms, for example rule-based lane follow or cruise mode.
