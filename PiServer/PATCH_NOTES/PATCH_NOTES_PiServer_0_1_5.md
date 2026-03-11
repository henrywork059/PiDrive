# PATCH NOTES — PiServer 0_1_5

## Goal
Add a dedicated camera settings page so camera tuning is no longer mixed into the calibration page, and make sure those settings can be saved and restored.

## Main changes
- Added a new **Camera** top tab in the web UI.
- Moved camera setup out of the Calibration page UI.
- Kept Calibration focused on motor trim, max speed, and turning ratio.
- Added camera controls for:
  - resolution
  - FPS
  - format
  - auto exposure
  - locked exposure time
  - analogue gain
  - exposure compensation
  - auto white balance
  - brightness
  - contrast
  - saturation
  - sharpness
- Extended runtime config so camera settings are saved in `config/runtime.json` and restored on reload.
- Added a separate `/api/camera/update` path so camera tuning can be applied from its own page.

## Notes
- Resolution / FPS / format changes may reopen the camera backend.
- Exposure / colour changes are applied live when supported by the backend.
- The active drive mode stays active while the Camera page is open.
