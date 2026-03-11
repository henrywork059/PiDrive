# PATCH NOTES — PiServer 0.1.3

## Goal
Reduce CPU, I/O, and backend pressure so the Raspberry Pi stays more responsive while running AI, live streaming, and self-driving logic at the same time.

## Main issues found

1. The MJPEG endpoint was repeatedly JPEG-encoding frames for every stream loop.
2. The MJPEG generator busy-looped when no frame was ready.
3. The control loop pulled extra frame copies for AI and recording.
4. Model inference repeatedly fetched tensor metadata on every prediction.
5. The recorder flushed JSONL metadata every frame, creating unnecessary disk I/O.
6. The web UI sent too many control updates while dragging the joystick.
7. The status endpoint recomputed Git status too often, which is expensive on Pi storage.
8. `/api/control` returned a full runtime snapshot even though the frontend only needed an acknowledgement.

## Final changes

### Backend
- `CameraService` now caches the latest JPEG for the web stream.
- Added frame sequence tracking and a wait/notify path so the stream waits for fresh frames.
- Normalized 4-channel camera frames down to 3-channel BGR where needed.
- Added a packet-style camera read so the control loop gets a matching frame and frame sequence together.

### AI / inference
- `ModelService` now caches TFLite input/output details after model load.
- Added internal inference throttling with cached last prediction reuse.
- Kept prediction fallback behavior safe when the model is missing or inference fails.

### Control loop
- Reworked algorithm calls so they consume the frame already fetched by the control loop.
- Avoided building a full state snapshot unless recording is actually enabled.
- Switched loop timing to `time.perf_counter()` for tighter timing.

### Recording
- Recorder metadata writes are now batched with timed flushes instead of flushing every frame.
- Recording format remains unchanged.

### Web / API
- `/api/control` now returns a lightweight acknowledgement.
- Joystick/control updates are throttled in the browser to reduce request spam.
- Status polling interval was relaxed slightly.
- Git status is cached in `UpdateService` so it is not recomputed on every status poll.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/algorithms/base.py`
- `PiServer/piserver/algorithms/manual.py`
- `PiServer/piserver/algorithms/auto_steer.py`
- `PiServer/piserver/algorithms/autopilot.py`
- `PiServer/piserver/algorithms/stop.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/services/model_service.py`
- `PiServer/piserver/services/recorder_service.py`
- `PiServer/piserver/services/update_service.py`
- `PiServer/piserver/web/static/app.js`
- `PiServer/README.md`

## Verification
- Python compile check passed with `python -m compileall PiServer`.
- JavaScript syntax check passed with `node --check piserver/web/static/app.js`.
- Flask server launch could not be fully tested in this container because `flask` is not installed here.

## Suggested runtime settings for Pi
- Start with `426x240` resolution.
- Start with `24` or `30 FPS`.
- Keep only one browser client connected to the MJPEG stream while driving.
- Test lane detection before enabling full auto.

## Future improvements
- Move model inference to a dedicated worker thread with a small latest-frame queue.
- Add an optional “Performance mode” switch in the web UI for lower stream FPS / lower JPEG quality.
- Add a camera low-res inference stream separate from the viewer stream.
- Add telemetry for control-loop latency and inference time.
