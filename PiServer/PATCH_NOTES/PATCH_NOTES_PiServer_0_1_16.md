# PATCH NOTES — PiServer_0_1_16

## Purpose
Make the Camera tab use a real live preview path when the camera backend is available, instead of silently falling back without any visibility.

## What changed
- Improved camera startup so PiServer tries safer Picamera2 formats before giving up.
- Added automatic retry if the camera backend is temporarily unavailable.
- Normalized captured frames before JPEG encoding so the MJPEG stream works more reliably with Picamera2 frame formats.
- Added live preview status to runtime state so the UI can tell whether it is showing a real camera frame or a generated placeholder.
- Added camera preview metadata text under the viewer panel.
- Refreshes the preview stream again when the Camera tab opens or after camera apply/reload.

## Files changed
- `PiServer/piserver/core/runtime_state.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/static/styles.css`
- `PiServer/README.md`

## Notes
- A real CSI camera preview still requires `picamera2` / libcamera to be available on the Pi.
- If the backend cannot open the camera, the UI now says clearly that it is showing a placeholder preview and includes the last backend error.

## Verification done here
- Python syntax compile passed.
- JavaScript syntax check passed.
