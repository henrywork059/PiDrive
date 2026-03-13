# PATCH NOTES — PiServer_0_1_18

## Goal
Reduce camera preview latency on the Pi and make camera resolution/performance tuning clearer from the Camera tab.

## Main changes
- Reworked the MJPEG preview path to use a **cached latest JPEG frame** instead of re-encoding on every browser send loop.
- Added **wait-for-new-frame** streaming so the browser receives the latest preview frame instead of rapidly resending stale ones.
- Added cache-control headers on `/video_feed` to reduce browser buffering.
- Added **Preview FPS** and **Preview JPEG quality** controls to the Camera settings.
- Added a **Resolution preset** selector in the Camera tab to make lower-latency capture sizes easier to pick.
- Kept the existing width/height controls so you can still set a custom resolution manually.
- Kept Picamera2 as the preferred backend, with a safer low-buffer configuration attempt for lower latency.

## Why the old build felt delayed
The previous preview path could keep re-encoding and re-sending frames too aggressively. That increased CPU load and made the browser more likely to show delayed frames.

## Expected result
- Lower live-preview latency in the browser.
- Lower CPU pressure from the preview path.
- Easier camera tuning for performance: lower resolution, lower preview FPS, and lower JPEG quality all help.

## Changed files
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/templates/index.html`

## Validation performed
- Python syntax compile passed.
- JavaScript syntax check passed.

## How to test on the Pi
1. Replace the files from this patch.
2. Start PiServer:
   `python3 server.py`
3. Hard refresh the browser.
4. Open the **Camera** tab.
5. Try these low-latency settings first:
   - Resolution preset: `426 × 240` or `320 × 180`
   - Capture FPS: `20` or `15`
   - Preview FPS: `10` to `12`
   - Preview JPEG quality: `50` to `60`
6. Click **Apply + Restart camera**.
7. Compare the preview delay before and after.

## Notes
- Lower capture resolution gives the biggest latency improvement.
- If you need more detail later, you can raise resolution again after verifying control responsiveness.
