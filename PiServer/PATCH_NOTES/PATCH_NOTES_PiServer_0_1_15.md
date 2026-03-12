# PATCH NOTES — PiServer_0_1_15

## Purpose
Add a dedicated Camera tab so camera work is separated from driving/runtime tuning.

## What changed
- Added a new **Camera** top tab in the web UI.
- Added a new **Camera settings** panel with controls for:
  - width
  - height
  - FPS
  - pixel format
  - auto exposure
  - exposure time
  - analogue gain
  - exposure compensation
  - auto white balance
  - brightness
  - contrast
  - saturation
  - sharpness
- Added a **Camera preview** panel using the existing MJPEG stream.
- Added **Apply + Restart camera** button.
- Added **Reload camera settings** button.
- Added backend routes:
  - `GET /api/camera/config`
  - `POST /api/camera/apply`
- Expanded config save/reload so camera settings are stored together with runtime settings.

## Backend changes
- `camera_service.py`
  - now stores camera configuration values
  - can apply settings at runtime
  - can restart the camera backend cleanly
  - tries to use Picamera2 controls when available
  - falls back to OpenCV or placeholder frame if needed
- `control_service.py`
  - now includes camera settings in config save/reload
- `app.py`
  - now serves camera config/apply routes
  - loads saved camera config on startup before the camera begins streaming

## UI changes
- New Camera tab layout.
- On the Camera tab:
  - drive/manual/record panels are hidden
  - camera preview, camera settings, status, and system/config remain available
- The existing viewer panel is used as the camera preview panel.

## Notes / limitations
- Some image controls only apply on the **Picamera2** backend.
- On **OpenCV** fallback, only a subset of settings may apply.
- The browser may need one hard refresh after replacing files so the new `0_1_15` JS/CSS loads.

## Verification done here
- Python syntax compile passed.
- JavaScript syntax check passed.

## Not fully tested in this container
- Full Flask app launch was not tested here because `flask` is not installed in this container.
- Real Pi camera behavior must be tested on the Pi itself.
