# PATCH NOTES — piTrainer_0_3_16

## Changes
- Reworked Path Preview so it reads more like turning motion while still ending at the same target point.
- Raised Playback Control max FPS from 30 to 100.

## Details
- Path Preview now uses a cubic turning curve: it starts nearly straight from the mid-bottom anchor, then bends into the target point like a forward-turning path.
- The endpoint still matches the same speed/steering target mapping.
- Playback FPS spin box now allows up to 100 fps.

## Verification
- Python compile check passed on patched files.
- Patch zip contains only changed files with the same wrapper-folder structure as before.
