# PATCH NOTES — PiServer_0_1_17

## Main goal
Fix the camera preview patch regression from `0_1_16` and restore a real manual-control + preview flow on the Pi.

## Problems found
1. `/api/control` crashed with:
   - `AttributeError: 'RuntimeState' object has no attribute 'maintenance_mode'`
2. The newer camera service had drifted away from the older working Pi camera flow, making it harder to get a real Picamera2 preview.
3. On restart/open failures, the camera path could fall back too quickly and leave the UI on placeholder preview.

## Changes in this patch
### 1) Fixed stale maintenance-mode dependency
- Updated `control_service.py` so it no longer assumes `maintenance_mode` exists in the runtime state.
- All maintenance-mode checks now use a safe fallback (`False`) when that field is absent.
- This removes the `/api/control` 500 crash while keeping the rest of the control flow unchanged.

### 2) Reworked camera backend closer to the older working PiCar camera code
- Replaced the camera loop with a **Picamera2-first** background capture flow modeled on the older PiCar camera logic.
- Added a short one-off colour calibration pass to stabilise preview colours after startup.
- Kept corrected BGR frames available for control/recording and JPEG preview.
- Preserved runtime camera settings and camera restart/apply support.

### 3) Safer backend opening behavior
- Picamera2 is still preferred first.
- OpenCV fallback is kept only as a secondary fallback.
- Preview/live/error state is updated more clearly so the Camera tab can tell you whether the stream is really live or only showing a placeholder.

### 4) Cache busting
- Updated the backend app version to `0_1_17` so the browser loads the new JS/CSS-linked page version cleanly.

## Files changed
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_17.md`

## What to test on the Pi
1. Start PiServer normally.
2. Open the web UI and move the manual control pad.
3. Confirm `/api/control` no longer returns a 500 error.
4. Open the **Camera** tab.
5. Confirm the preview says **live preview** instead of placeholder, if Picamera2 is working.
6. Try **Apply + Restart camera** once and confirm preview comes back.

## Notes
- This patch does **not** re-add the web update/restart feature.
- You are still using terminal `git pull` for code updates.
- If the camera still falls back to placeholder after this patch, the next thing to check is whether `picamera2` and libcamera are working correctly on the Pi outside PiServer.
