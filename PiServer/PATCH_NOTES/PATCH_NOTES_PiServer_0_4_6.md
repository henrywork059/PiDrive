# PATCH NOTES — PiServer_0_4_6

## Baseline
- Stable baseline: `PiServer_0_4_0`
- Previous active patch: `0_4_5`
- This patch is built forward on top of the existing `0_4_x` line and keeps the recent `0_4_2` to `0_4_5` UI / snapshot-folder work intact.

## Request summary
Fix two real PiServer runtime problems:
1. preview is live, but saved snapshots are placeholder images instead of the live camera image
2. after steering-direction calibration, reverse driving still feels inverted when backing up

## Problems found
### 1) Snapshot route was reading the wrong frame source
The snapshot API used:
- `camera_service.get_latest_frame()`

But PiServer can have a live browser preview without keeping a fresh BGR processing frame cached. In that case:
- the browser MJPEG / JPEG preview is live
- `get_latest_frame()` can still return the placeholder frame or a stale fallback
- the saved snapshot becomes a placeholder image even though the preview is correct

### 2) Reverse steering did not stay consistent with travel direction
`MotorService._map_drive_locked()` applied `steering_direction` the same way for both positive and negative throttle.

That meant once steering was calibrated for forward driving, backing up could still feel flipped because the turn mix did not adapt to reverse travel.

## Root causes
- Snapshot capture reused the general display-frame cache instead of requesting a real live frame for snapshot saving.
- Camera access was not serialized for an on-demand snapshot grab versus the background preview loop.
- Steering mix logic did not account for the change in travel direction when throttle is negative.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/piserver/services/motor_service.py`
- `PiServer/tests/test_camera_service.py`
- `PiServer/tests/test_motor_service.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_6.md`

## Exact changes made
### Snapshot capture
Updated `piserver/services/camera_service.py` to add a dedicated live snapshot-frame path:
- new `capture_snapshot_frame()` helper
- prefers an already cached raw live frame when one exists
- otherwise grabs a fresh live frame directly from Picamera2 / OpenCV
- updates the raw-frame cache with that live image
- never intentionally falls back to the placeholder display frame for snapshot saving
- serializes direct camera reads with a capture lock so the background preview loop and on-demand snapshot capture do not fight over the same backend

Updated `piserver/app.py` so `/api/record/capture_once` now uses that live snapshot-frame helper instead of `get_latest_frame()`.

### Reverse steering behavior
Updated `piserver/services/motor_service.py` so the effective steering sign now flips when throttle is negative before the saved `steering_direction` calibration is applied.

Result:
- forward steering calibration still works as before
- reverse driving now keeps turn feel consistent with travel direction instead of feeling inverted when backing up

### Versioning
- Bumped `APP_VERSION` in `piserver/app.py` from `0_4_5` to `0_4_6`

## Resulting behavior
After applying this patch:
- clicking **Snapshot** saves the live camera image to the shared snapshot folder instead of saving the placeholder preview image
- snapshots still stay in the single shared `PiServer/data/records/snapshots` folder introduced/fixed in `0_4_5`
- steering-direction calibration still works
- backing up no longer feels directionally inverted after setting steering inverse

## Verification actually performed
Ran locally in the uploaded PiDrive repo copy:
1. Python syntax check:
   - `python3 -m py_compile piserver/app.py piserver/services/camera_service.py piserver/services/motor_service.py tests/test_camera_service.py tests/test_motor_service.py`
2. Full PiServer unit tests:
   - `python3 -m unittest discover -s tests -q`
3. Added and passed new tests covering:
   - snapshot capture preferring a direct live camera frame when no raw cache is present
   - snapshot capture reusing an existing raw live frame when available
   - reverse throttle flipping the steering bias direction
   - reverse throttle still respecting saved `steering_direction = -1` calibration

## Known limits / notes
- This patch fixes PiServer’s own snapshot path. It does not alter external scripts that may save camera frames outside PiServer.
- The reverse steering fix is based on travel-direction semantics for backing up, which matches the reported real-car behaviour.
- No layout/style files were changed in this patch, so the recent `0_4_2` to `0_4_4` UI work and the `0_4_5` snapshot-folder fix remain intact.
