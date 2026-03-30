# PATCH NOTES — PiServer_0_4_7

## Baseline
- Stable baseline: `PiServer_0_4_0`
- Previous active patch: `0_4_6`
- This patch is built forward on top of the accepted `0_4_6` snapshot-folder and reverse-steering fixes.
- No `0_4_2` to `0_4_6` UI/style work was removed or replaced.

## Request summary
Fix the remaining snapshot bug:
- the first saved snapshot is correct
- later snapshots keep saving that same first image instead of the current live image

## Problem found
The `0_4_6` snapshot path still had one stale-cache failure mode.

`CameraService.capture_snapshot_frame()` did this in the wrong order:
1. read `get_raw_frame()` first
2. only attempt a fresh direct camera capture if the raw cache was empty

That meant:
- the first snapshot could be correct because it seeded `_raw_frame`
- later snapshot requests in preview-only/manual mode could keep reusing that cached first frame
- the browser preview still looked live, so the bug only showed up in the saved files on disk

## Root cause
PiServer preview and PiServer snapshot are not the same cache path.

In manual / preview-first use, PiServer can keep the browser preview live through the JPEG preview pipeline while `_raw_frame` is not being refreshed every cycle.
After the first snapshot, `_raw_frame` held that old image and the snapshot helper trusted it too early.

## Files changed
- `PiServer/piserver/app.py`
- `PiServer/piserver/services/camera_service.py`
- `PiServer/tests/test_camera_service.py`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_7.md`

## Exact changes made
### 1) Snapshot capture now prefers a fresh live frame
Updated `piserver/services/camera_service.py` so `capture_snapshot_frame()` now:
- checks for an active camera backend first
- requests a fresh direct frame from Picamera2 / OpenCV before trusting cached raw data
- updates the raw-frame cache only after a successful fresh live capture

Result:
- repeated snapshot presses now keep pulling a new live frame
- the first snapshot is no longer reused as the source for later snapshots

### 2) Added cache-age protection for fallback behavior
Added raw-frame age tracking so cached raw frames are only used as a fallback when they are still fresh.

This protects against stale-image reuse if:
- direct capture is temporarily unavailable, or
- PiServer only has an old raw frame left from earlier activity

### 3) Version bump
Updated `APP_VERSION` in `piserver/app.py` from `0_4_6` to `0_4_7` for cache-busting after file replacement.

## Verification actually performed
Ran locally in the uploaded PiDrive repo copy after applying the patch on top of `0_4_6`.

### Reproduced the old bug path
Confirmed that the pre-fix `0_4_6` logic returned the cached first frame and did **not** call direct live capture once `_raw_frame` already existed.

### Automated checks run
1. Python syntax check:
   - `python3 -m py_compile piserver/app.py piserver/services/camera_service.py tests/test_camera_service.py tests/test_motor_service.py tests/test_recorder_service.py`
2. Full PiServer unit tests:
   - `python3 -m unittest discover -s tests -q`
3. Result:
   - `23 tests passed`

### Added / updated tests
`tests/test_camera_service.py` now verifies:
- direct live capture is used when the raw cache is empty
- direct live capture is still used even when an older cached frame already exists
- a fresh cached raw frame can still be used as a safe fallback
- a stale cached raw frame is rejected instead of being silently reused

## Expected result after applying
- every snapshot press should save the current live camera image, not the first previously saved image
- snapshots still save into the same shared folder introduced/fixed earlier:
  - `PiServer/data/records/snapshots`
- snapshot ZIP download behavior remains unchanged
- reverse steering behavior from `0_4_6` remains intact

## Known limits / notes
- This patch fixes PiServer's internal snapshot source-selection logic. It does not change external scripts that might save images separately.
- If the camera backend itself stops delivering new frames, PiServer will now prefer failing safely over silently reusing a stale old snapshot frame.
