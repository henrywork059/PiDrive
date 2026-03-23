# PATCH NOTES — CustomDrive 0_1_5

## Goal
Tighten the competition manual-control app so it follows PiServer more closely, is easier to manage/debug, and avoids browser-side control/preview behavior that drifted away from the main PiServer pattern.

## Main review findings
1. The manual-control app reused PiServer services, but its Flask app and browser layer had drifted from PiServer’s route/preview style.
2. The browser sent a control POST on nearly every joystick/keyboard change with no throttling, which could spam the Pi and make debugging harder.
3. The manual app used a separate MJPEG-style preview flow instead of PiServer’s polled JPEG preview approach.
4. The launcher printed only `127.0.0.1`, which made remote access more confusing even when the service was healthy.
5. A few browser-side state sync paths were weaker than PiServer’s behavior, especially when reloading runtime/session state.

## What changed

### 1) Manual app aligned more closely with PiServer
Updated `custom_drive/manual_control_app.py` so the app now:
- stores service references under `app.config["services"]` like PiServer
- exposes `api/algorithms`
- keeps `api/control` compatible with PiServer-style payloads (`algorithm`, `current_page`, `max_throttle`, `steer_mix`, manual steering/throttle)
- adds `api/algorithm/select`
- adds PiServer-style `api/camera/apply` and `api/motor/apply`
- keeps the manual page forcing the `manual` algorithm by default

### 2) Browser control updates throttled
Updated `custom_drive/manual_web/static/app.js` so manual steering/throttle updates are queued and rate-limited instead of POSTing as fast as pointer/key events arrive.

This should reduce needless request spam and make the real motor path steadier and easier to trace.

### 3) Preview path changed to PiServer-style frame polling
Updated the manual-control web page to use PiServer-style repeated requests to `/api/camera/frame.jpg` instead of relying on a separate always-on MJPEG image source.

This keeps the preview flow closer to the main PiServer UI and is generally easier to reason about when debugging browser refresh issues.

### 4) Better state sync and safer browser behavior
The browser now:
- syncs `max_throttle` and `steer_mix` back from server status
- resets controls on page blur/visibility loss
- pauses/resumes preview activity more cleanly
- keeps the session/config UI in sync after reload/save

### 5) Launcher prints better URLs
Updated `run_custom_drive_manual.py` so it prints the localhost URL and likely LAN URLs, making it clearer which address to open from another device.

## Files changed
- `CustomDrive/custom_drive/manual_control_app.py`
- `CustomDrive/custom_drive/manual_web/static/app.js`
- `CustomDrive/custom_drive/manual_web/templates/index.html`
- `CustomDrive/run_custom_drive_manual.py`
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_5.md`

## Verification performed
- Python compile check for updated CustomDrive manual-control files
- basic static review against `PiServer/piserver/app.py` and `PiServer/piserver/web/static/app.js`

## Notes
- This patch keeps the manual-control app separate from the main autonomous CustomDrive runtime, but makes its service wiring and browser behavior much closer to PiServer.
- Real motor output still depends on the Pi actually using PiServer `MotorService` with GPIO available.
