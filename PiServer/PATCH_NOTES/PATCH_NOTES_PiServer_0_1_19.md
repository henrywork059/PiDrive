# PATCH NOTES — PiServer 0_1_19

## Goal
Reduce camera preview latency further, stop wasting work when preview/AI is not in use, and add a clearer streaming-quality control.

## Main changes
- Reworked camera preview path to use **latest-frame JPEG polling** from `/api/camera/frame.jpg` instead of relying on the browser to buffer the MJPEG stream.
- Added **Streaming quality** selector in Camera settings:
  - `Low latency`
  - `Balanced`
  - `High quality`
  - `Manual`
- Kept manual control of:
  - preview FPS
  - preview JPEG quality
  - capture resolution
- Camera preview is now **paused automatically when the browser tab is hidden**.
- Backend preview encoding is now **disabled when preview is not active**.
- Camera backend now lowers capture load when:
  - preview is not active
  - AI is not using frames
  - recording is off
- Auto-steer / autopilot now read the latest frame **without an extra defensive copy**.
- Control loop now only fetches a copied frame for the recorder when recording is actually enabled.
- Camera apply flow now explicitly stops preview, restarts camera, waits briefly, reloads config, and then resumes preview.

## Why this should help latency
The biggest browser-side source of delay was the preview path buffering older JPEG frames. The new flow always asks for the **newest cached JPEG only**, so the page should stay closer to real time.

The backend also now avoids unnecessary preview JPEG work and reduces capture load when only idle/manual use is happening.

## Files changed
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/algorithms/auto_steer.py`
- `PiServer/piserver/algorithms/autopilot.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/piserver/web/templates/index.html`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_1_19.md`

## Validation steps
1. Replace the files from this patch into your current PiServer folder.
2. Start PiServer:
   ```bash
   cd ~/PiDrive/PiServer
   python3 server.py
   ```
3. Hard-refresh the browser.
4. Open the **Camera** tab.
5. Test these settings first:
   - Resolution preset: `320 × 180` or `426 × 240`
   - Capture FPS: `15` or `20`
   - Streaming quality: `Low latency`
6. Click **Apply + Restart camera**.
7. Check whether preview delay is reduced.
8. Hide the browser tab for a few seconds, then return, and confirm preview resumes.
9. Test manual drive and then AI mode to confirm control remains responsive.

## Notes
- `/video_feed` still exists, but the desktop page no longer depends on it for the main preview.
- If you want even lower latency later, the next step would be a dedicated low-resolution preview stream completely separated from the model/recording frame size.
