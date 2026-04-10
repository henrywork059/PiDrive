# PATCH NOTES — CustomDrive_0_5_7

## Request summary
Investigate and patch the Mission 1 freeze that appears after the detection loop starts.

Observed user symptom:
- the Mission 1 web GUI appears to freeze or become unresponsive once the AI detection phase begins

## Baseline / rollback review
This patch was built forward from the latest accepted Mission 1 patch line available in the workspace:
- `CustomDrive_0_5_6.zip`

Before patching, the recent Mission 1 patch-note history was reviewed to reduce rollback risk:
- `PATCH_NOTES_CustomDrive_0_5_3.md`
- `PATCH_NOTES_CustomDrive_0_5_4.md`
- `PATCH_NOTES_CustomDrive_0_5_5.md`
- `PATCH_NOTES_CustomDrive_0_5_6.md`

Accepted behavior intentionally preserved:
- start route still runs before camera/model startup
- camera boot -> model load -> detection loop order is unchanged
- Mission 1 pickup / drop-off state machine is unchanged
- route motion fixes from `0_5_6` remain unchanged
- box drawing, detection list, centered coordinates, and FPS reporting remain unchanged
- arm pose logic remains unchanged

## Cause / root cause
The main issue found in the actual current Mission 1 code was in the **web refresh logic**, not the detector backend itself.

### What the page was doing before this patch
Once the Mission 1 phase entered `ai_*`, the browser started doing two expensive things repeatedly:

1. **Status polling**
   - `setInterval(refresh, 400)` kept calling `/api/status`
   - there was **no in-flight guard**, so if one refresh was slow, the next refresh could start anyway
   - that allowed overlapping `/api/status` requests to pile up

2. **Frame refreshes coupled to status refreshes**
   - every time `renderViewer(status)` ran during AI mode, it forced:
     - `video.src = /api/frame.jpg?t=...`
   - so the browser kept starting new JPEG fetches directly from the status refresh cadence
   - when status refreshes overlapped, frame reloads also overlapped

### Why that can freeze the page in practice
Once the Mission 1 detection loop starts, the page becomes heavier because it is rendering:
- live status
- detections table
- overlay SVG boxes
- viewer summary cards
- event log
- repeated image reloads

On the Pi / browser combination, overlapping status requests plus overlapping image reloads can create a request/render pile-up that **looks like the page froze** right after AI starts.

This matches the reported timing very closely: the page is fine before the detection loop, then freezes once AI mode starts and frame reloads begin.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_7.md`

## Exact behavior changed

### 1. Status refresh is now single-flight
The Mission 1 web page now prevents overlapping `/api/status` requests.

A refresh-in-flight guard was added so the page will not start a second status poll while the previous one is still running.

Result:
- no status-request pile-up
- less browser / Pi load during AI mode
- more stable page responsiveness

### 2. The page no longer reloads the frame from inside every status render
Previously, every AI-mode status render forced a new:
- `/api/frame.jpg?t=...`

That tied frame fetches directly to status polling and made the viewer aggressively reload images whenever status refreshed.

This patch separates those two loops.

Result:
- status rendering still updates text / detections / overlay
- frame JPEG reloads are now driven by a separate throttled frame loop
- viewer image reloads no longer explode when status refreshes slow down

### 3. Frame refresh is now throttled and single-flight
A dedicated frame refresh loop was added:
- `FRAME_REFRESH_MS = 250`

It now:
- checks whether AI live view should be shown
- only starts a new frame request when there is **no frame request already in flight**
- clears the in-flight flag on image load / error
- uses a fallback timeout so a stuck image load does not permanently block future updates

Result:
- frame loading becomes controlled and self-recovering
- the browser does not keep stacking image fetches

### 4. Status refresh now uses a self-scheduled loop instead of a blind fixed interval
The old code used:
- `setInterval(refresh, 400)`

This patch changes that to a self-scheduled loop using:
- `STATUS_REFRESH_MS = 600`
- `scheduleRefresh()` after each completed refresh

That means the next poll is scheduled **after the previous poll finishes**, instead of blindly launching new requests on a timer.

Result:
- less request overlap
- more stable behavior on slower Pi/browser hardware

### 5. Static asset version was bumped
`APP_VERSION` was changed from:
- `0_5_6`

to:
- `0_5_7`

This forces the browser to fetch the updated Mission 1 `app.js` instead of reusing the cached older script.

## Verification actually performed
The following checks were actually performed in the patch workspace:

1. Reconstructed the current accessible Mission 1 workspace by layering the repo snapshot with the accepted Mission 1 patch line through `0_5_6`.
2. Reviewed recent patch notes `0_5_3` through `0_5_6` before editing to reduce rollback risk.
3. Inspected the actual current Mission 1 web code and confirmed:
   - `/api/status` refreshes were driven by `setInterval(refresh, 400)`
   - there was no in-flight request guard
   - AI-mode viewer rendering reset `video.src` on every status render
4. Patched the web refresh loop to:
   - prevent overlapping status polls
   - split status refresh and frame refresh into separate loops
   - throttle frame reloads and keep only one frame request in flight
5. Updated `APP_VERSION` to bust browser cache for the fixed script.
6. Ran:
   - `node --check CustomDrive/custom_drive/mission1_web/static/app.js`
   - `python -m py_compile CustomDrive/custom_drive/mission1_session_app.py`
7. Checked the patch zip structure to ensure it is patch-only with the correct top-level `CustomDrive/` folder.

## Known limits / next steps
1. This patch addresses the most likely **web freeze** cause found in the current code path.
   - it does not redesign the detector backend itself
   - if the TFLite model is extremely slow, the Mission 1 loop can still feel slow even if the page no longer freezes

2. The current status payload still includes a fairly rich event log and full detection list.
   - this patch leaves that behavior unchanged because the request pile-up was the more direct current bug
   - if needed later, the next optimization would be trimming the live event payload further in AI mode

3. The frame is still served as repeated JPEG snapshots.
   - this patch stabilizes that pattern
   - a later patch could switch to a more efficient stream approach if you want even smoother live viewing
