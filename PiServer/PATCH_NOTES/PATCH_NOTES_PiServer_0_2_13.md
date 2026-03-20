# PiServer 0_2_13 Patch Notes

## Main fix
- Fixed a camera preview recovery bug where PiServer could show one real frame and then fall back to the placeholder forever if the live camera backend started failing after startup.

## What changed
- Added camera backend failure counting and automatic backend reopen/retry in `piserver/services/camera_service.py`.
- Reset failure counters after successful captures and successful backend opens.
- Added a `stop()` alias in `CameraService` so app shutdown and restart paths are safer and match the existing cleanup call in `piserver/app.py`.
- Bumped the web app version to `0_2_13` in `piserver/app.py` so the browser is more likely to refresh the latest static assets.

## Why this matters
Previously, if Picamera2 or OpenCV delivered an initial frame and then started returning capture errors, PiServer kept the broken backend open and continued serving placeholder JPEGs. The new logic tears the failed backend down after repeated capture failures so the background loop can reopen the camera cleanly.

## Files in this patch
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_2_13.md`

## Apply
Copy these files over the matching paths in your existing `PiServer` folder, then restart PiServer.
