# CustomDrive 0_2_12 Patch Notes

## Request summary
Fix the GUI freezing/crashing after some time or after AI deploy/actions.

## Cause / root cause
The current GUI was combining several risky behaviors on the Pi:
- a long-lived MJPEG `/video_feed` stream
- aggressive `/api/status` polling every 350 ms
- repeated preview stream reloads after AI actions
- AI config saves that could redeploy the detector again immediately after a successful deploy
- no guard against overlapping TFLite inference calls when preview requests stacked up

That combination made the Pi camera + OpenCV + TFLite path heavier and more fragile than it needed to be.

## Files changed
- `CustomDrive/custom_drive/gui_control_app.py`
- `CustomDrive/custom_drive/gui_web/templates/index.html`
- `CustomDrive/custom_drive/gui_web/static/app.js`
- `CustomDrive/custom_drive/object_detection_service.py`

## Exact behavior changed
- Switched the GUI preview path from long-lived MJPEG streaming to single-frame JPEG polling using `/api/camera/frame.jpg`.
- Added one-at-a-time preview fetching on the browser side so the next preview frame is only requested after the previous one has loaded or failed.
- Reduced status polling from 350 ms to 1000 ms and prevented overlapping status requests.
- Stopped AI config saving from blindly rebuilding/redeploying the detector after a successful deploy.
- Added a non-blocking inference lock so overlapping preview requests reuse cached detections instead of trying to invoke TFLite concurrently.
- Reduced regular `/api/status` payload cost by omitting the model list there; the model list still comes from `/api/ai/models`.
- Bumped the GUI asset version to `0_2_12` so the new frontend code is more likely to load after restart.

## Verification performed
- Reconstructed the latest accepted CustomDrive state from the `CustomDrive_0_2_0` baseline plus accepted `0_2_1` to `0_2_11` patches before editing.
- Ran `python -m compileall CustomDrive`.
- Checked that the patch stays forward-compatible with the working arm-control behavior from `0_2_10`.

## Known limits / next steps
- I could not reproduce the Pi-side segmentation fault in this container because the native camera/TFLite stack is not available here.
- If the Pi still crashes after this patch, the next check should be whether the crash is in Picamera2/libcamera shutdown or in a specific model output path for the uploaded detector.
