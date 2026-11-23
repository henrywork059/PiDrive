# PATCH NOTES — CustomDrive_0_5_18 (U22: Mission 1 bounded recovery and stage outcomes)

## Request summary
Implement the fail-closed Mission 1 portion of roadmap **U22**: explicit failure reasons, bounded camera/target searches, checked arm-pose stage results, operator-controlled restart, and compact mission reports. Preserve the accepted UI, grip/drop-off trigger meanings, live camera updates during pose motion, and recent motor calibration improvements.

## Verified baseline and anti-rollback
- Built on live GitHub **CustomDrive 0_5_17 draft PR #11**, not an older monorepo snapshot. Confirmed `mission1_session_app.py` and `mission1_web/static/app.js` match the uploaded 0_5_17 patch and current GitHub blob hashes before editing.
- Reviewed `PATCH_NOTES_CustomDrive_0_5_17.md`, `0_5_16.md`, `0_5_15.md`, and `0_5_14.md` (including the previously fixed stuck-preview and pose-settle symptoms).
- Keeps pickup classes 1/2, drop-off class mapping 3/4, stop-before-grip/release, nonblocking frame refresh during pose transitions, saved arm roles and angles, independent motor calibration versus software turn mapping, `reverse_after_release_s`, camera preview guides and existing config data.
- Does not modify shared PiServer hardware ownership changes in pending PR #16, nor the legacy piCar component.

## Root causes and risks found
1. Mission 1 rotated during target search indefinitely if no matching class was detected. A lost camera frame caused a temporary stop but never escalated to a terminal fault. A cached camera frame could be reused without checking its true capture age.
2. Return values from `_load_arm_role_pose()` were ignored in several active pickup, lift, release and starting-position paths; a failed servo command could still advance the mission state and record an assumed held object.
3. The active detection loop used the **drop-off threshold for pickup** and the **pickup threshold for drop-off**, reversing the accepted 0_5_16 independent-trigger semantics even though the guide overlay from 0_5_17 was drawn correctly.
4. `stop_session()` cleared the thread pointer and released shared resources even if its three-second join timed out, allowing a restart while the old worker might still control the camera or arm.
5. There was no compact saved mission terminal report; the UI did not expose stable, structured failure codes.

## Files changed
- `CustomDrive/custom_drive/mission1_session_app.py`
- `CustomDrive/custom_drive/mission_safety.py` (new)
- `CustomDrive/custom_drive/mission1_web/static/app.js`
- `CustomDrive/tests/test_mission1_recovery.py` (new)
- `CustomDrive/README.md`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_5_18.md` (new)

## Exact behavior changed
1. Mission 1 checks the PiServer camera adapter's `get_raw_frame_age()` before inference and motor commands. If a cached frame is older than the configured default 2 seconds, or no frame arrives within the timeout, it stops and fails with `frame_stale`. A fresh frame resets the no-frame window. The timeout is clamped to 0.25–30 seconds.
2. Pickup and drop-off searches have a bounded default 20-second window per search state, clamped to 2–300 seconds. Failure stops the motors with `retry_exhausted`; the mission cannot quietly resume moving on renewed detections.
3. Loss of a previously locked target stops immediately with `target_lost` rather than silently restarting clockwise search. No blind autonomous back-out is attempted without fresh location data; manual operator restart is required.
4. Starting, grip-ready, grip, lift, release and return-to-start arm poses now check their success results. Any failed pose stops movement and fails with `arm_unavailable`; no subsequent class release/hold-state update is performed.
5. A successful servo command is *not* a grip-sensor measurement. The status and report expose `grip_confirmation` as `pose_applied_unverified` (or `not_sensor_confirmed`) and the web page displays **Assumed held** instead of claiming a physically confirmed grasp.
6. Pickup now correctly uses `arm.grip_trigger_y_ratio`, and drop-off uses `arm.dropoff_trigger_y_ratio`. Their existing meaning remains **100% = top, 0% = bottom**, with no model, frame-space or UI-slider reinterpretation.
7. A completed/failed/stopped worker writes one compact JSON report to `CustomDrive/mission_reports/mission1_<session-id>.json`, with a unique session ID, result, phase, reason, stage, assumed held class, and last 40 debug events. A completed file is published without overwriting an earlier report; temporary files are cleaned on errors.
8. The Mission 1 status endpoint now provides `mission_outcome`, `failure_reason`, `failure_stage`, `target_loss_count`, `grip_confirmation`, and `mission_report_path`; the existing status page shows these fields without changing the accepted layout arrangement.
9. Stopping a worker that refuses to exit after the join timeout now returns an error and **retains ownership of the camera/arm** rather than unloading the model and closing hardware behind an active worker. `close()` respects this decision. Operator Stop during pose transitions is recorded as `stopped`, not an arbitrary failure.
10. New normalized optional keys `mission.search_timeout_s` and `mission.frame_timeout_s` default safely when absent. Existing config values and unrelated keys are preserved. APP_VERSION advances to `0_5_18` for browser asset refresh.

## Verification actually performed
Against the 0_5_17-compatible CustomDrive source files from the uploaded repository and patch, matching the live GitHub PR #11 base:
- `cd CustomDrive && PYTHONPATH=. python -m unittest discover -s tests -p 'test_mission1_recovery.py' -v` — **18/18 passed**.
- `python -m compileall -q custom_drive run_custom_drive_web.py tests` — passed.
- `node --check custom_drive/mission1_web/static/app.js` — passed.
- `node tests/test_mission1_trigger_guides.cjs` — passed (existing 0_5_17 guide overlay behavior).
- Tests include malformed/clamped config, stale cached frame rejected before inference, no-frame timeout, bounded searches, target lock loss, absent arm backend, failure before driving the first route, failed release retaining assumed held state, explicit operator stop, refused hardware handover after a stuck worker, independent grip/drop-off threshold usage, and non-overwriting structured reports.
- Physical Raspberry Pi camera, actual arm servo motion, real TensorFlow Lite inference, full Flask browser interaction, and motor safety with wheels raised **have not been tested**. The environment lacked Flask; test harness uses a minimal import stub only for isolated backend logic.

## Known limitations and next steps
- This implements the **fail-closed bounded search and report path** of U22 for the active Mission 1 session runtime. The older generic `MissionController` and `MissionState` demo runtime retain their existing retry/back-out implementation; no broad rewrite or migration was attempted.
- There is currently **no physical grip/force sensor** in the accepted arm interface. Never interpret pose success as object capture confirmation. Optional true grip confirmation and operator-approved back-out planning remain future work.
- Search timeout and stale-frame checks run inside the mission loop, not as an independent motor-hardware watchdog. A blocked inference or servo call can still delay motor stopping. A separate motor-side watchdog is still necessary.
- A failed hardware stop can still mean actual motor motion did not cease; this update cannot guarantee an electrical cutoff. Confirm physical motor outputs with wheels raised before merge.
- Mission report creation is best-effort: if disk is full or filesystem links are unsupported, the failure remains visible in events/status but report file creation may fail. Reports are not intended as trainer labels or permissioned audit logs.
- The current automatic Mission 1 loop has no finite successful stop condition; reports are written on operator stop or failure rather than claiming mission completion without a completion criterion.
- Merge/review **CustomDrive PR #11** before this stacked PR. No ZIP deliverables and no unrelated component changes.
