# PATCH NOTES — PiServer 0_1_22

## Goal
Fix the camera preview colour regression by switching the web preview to a Picamera2-native image/JPEG path instead of the later NumPy/OpenCV colour path that was turning blue objects orange.

## What changed
- `piserver/services/camera_service.py`
  - Picamera2 preview frames now come from `capture_request()` + `request.make_image("main")`.
  - Web preview JPEG bytes are generated from the Picamera2/PIL image path instead of `capture_array()` + OpenCV JPEG encoding.
  - AI/recording frames from Picamera2 are built from the same PIL image so the frame path stays aligned with the colour-correct preview path.
  - OpenCV remains the fallback backend and still uses the OpenCV JPEG path when Picamera2 is unavailable.
- `piserver/app.py`
  - bumped asset/app version to `0_1_22` so the browser reloads the updated files.

## Why this patch
Terminal testing showed:
- `rpicam-hello` looked correct.
- Picamera2 native saves (`capture_file` / `request.save`) looked correct.
- Python `capture_array()` based saves looked wrong.

That strongly pointed to the array/OpenCV preview path as the source of the colour swap.

## Validation checklist
1. Replace the changed files with this patch.
2. Restart PiServer:
   - `cd ~/PiDrive/PiServer`
   - `python3 server.py`
3. Hard refresh the browser.
4. Open the **Camera** tab.
5. Test the previously wrong colour scene again.
6. Confirm **Apply + Restart camera** still reconnects the preview on the same tab.

## Files included in this patch zip
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/app.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_22.md`
