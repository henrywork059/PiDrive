# PATCH NOTES — PiServer 0.1.4

## Goal
Reduce Raspberry Pi runtime pressure further so CPU time is spent on driving and inference instead of idle background work.

## Main issue found
In 0.1.3, several parts were already improved, but the camera/stream path could still keep running even when the car was not in an AI mode and no user really needed frames. The web page also kept video and frequent status/Git polling alive in the background.

## Changes made

### 1) Demand-driven camera pipeline
- Added camera demand tracking inside `CameraService`.
- Camera backend now opens only when needed by:
  - AI modes (`auto_steer`, `autopilot`)
  - active recording
  - active MJPEG viewers
- When there is no demand, camera backend closes and the camera worker sleeps instead of constantly capturing frames.

### 2) Viewer-aware MJPEG streaming
- `/video_feed` now registers and unregisters stream clients cleanly.
- Stream demand is released when the client disconnects.

### 3) Hidden-tab load reduction
- Browser now drops the MJPEG stream when the tab is hidden.
- Stream is restored automatically when the tab becomes visible again.

### 4) Lighter status polling
- Normal runtime status polling slowed from 1.0s to 1.5s on visible tabs and 5.0s on hidden tabs.
- Git status moved to a dedicated endpoint and refreshes less often.

### 5) Less backend churn during driving
- Removed status-message rewrites on every manual joystick update and every runtime slider change.
- Camera demand is refreshed only when mode/recording/config changes require it.

## Expected result
- Lower idle CPU use in manual mode when camera view is not needed
- Less MJPEG/network overhead from background browser tabs
- More headroom for TFLite inference and vehicle responsiveness
- Less wasted backend work while the joystick is being dragged

## Files changed
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/README.md`

## Verification done
- Python syntax compile check
- JavaScript syntax check with Node
- Zip packaged with updated patch notes

## Suggested next step
The next larger speed gain would be a dedicated inference worker with a one-frame queue so camera capture, control timing, and TFLite invoke do not block each other.
