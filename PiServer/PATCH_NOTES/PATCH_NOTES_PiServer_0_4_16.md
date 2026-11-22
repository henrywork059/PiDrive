# PATCH NOTES — PiServer_0_4_16: recording storage safety (U26)

## Request summary
Implement U26 for PiServer: detect low free space before recording/snapshots, prevent continuous retries after disk writes fail, expose storage and session-size diagnostics, and keep historical cleanup manual and confirmed.

## Root cause / risk
`RecorderService.maybe_record` previously wrote JPEGs then appended JSONL in the motor-control loop without a free-space preflight or error trap. A failed `cv2.imwrite` could silently omit a frame, and an exception from JPEG or metadata writing could exit the control-loop thread. There was no per-session space/status diagnostic. Deletion had a browser confirmation but no required explicit flag in the delete API payload.

## Anti-rollback
- Built on **live PiServer 0_4_15 draft PR #23**, stacked on PRs #16, #15, #14 and #9.
- Reviewed notes 0_4_15, 0_4_14, 0_4_13 and 0_4_12, and the actual entry point `PiServer/server.py`.
- Preserved prior U23 latency metrics, U14 camera/motor ownership lock, U12 model preflight, F3 LAN session/token/CSRF authorization, 0_4_11 motor failsafes and watchdog, AWB camera defaults, layout and persistence.
- No config files, UI layout keys, physical motor outputs or legacy runtime files altered.

## Files changed
- `PiServer/piserver/core/recording_storage.py` (new)
- `PiServer/piserver/services/recorder_service.py`
- `PiServer/piserver/services/control_service.py`
- `PiServer/piserver/app.py` (delete confirmation and version 0_4_16)
- `PiServer/piserver/web/static/app.js` (explicit deletion payload only)
- `PiServer/tests/test_recording_storage.py` (new)
- `PiServer/tests/test_recorder_storage.py` (new)
- `PiServer/README.md`
- `PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_16.md` (new)

## Exact behavior
1. Capacity preflight checks the recorder filesystem before session creation, each JPEG, and one-shot snapshot. Environment overrides `PISERVER_RECORDING_WARN_FREE_MB` and `PISERVER_RECORDING_MIN_FREE_MB` configure the default 512 MiB warning/256 MiB critical reserve, including the anticipated write bytes. Missing storage telemetry fails closed only for recording.
2. On critical/unavailable capacity or a frame write/metadata append failure, stop **only** recording and retain the session/images/metadata. Catch ordinary write exceptions inside `RecorderService.maybe_record`, preventing the error from escaping into the active motor controller. Best-effort truncate the failing JSONL append to its prior position if possible; do not touch existing completed rows.
3. `ControlService.toggle_recording` catches start errors and returns a clear `ok=False` status/message without changing E-stop, manual lease or motor state; the control thread continues.
4. One-shot snapshot errors return a response instead of leaking an exception. Success state is committed only after its metadata append; any orphan image after failure is retained for inspection, not used as a fake training label.
5. Existing `/api/status` includes `recording_storage` (free/total bytes, state, thresholds, recent five errors, cached active/last session size and manual-only cleanup policy). `/api/record/sessions` includes `size_bytes` for each selected folder. The last queried size is cached for two seconds; each different folder in an explicit listing may be scanned. Status size scans run outside the recorder lock.
6. Existing browser `window.confirm` is preserved and sends `confirm:true` to the authenticated/CSRF-protected delete route. Server rejects missing confirmation before invoking the existing active-session and path protections. Nothing is automatically deleted or cleaned based on capacity.
7. `APP_VERSION` advances to `0_4_16`. All existing runtime routes and settings remain.

## Verification actually performed
- Locally verified PiServer recorder/service sources matched GitHub recorder baseline blob before modification.
- `python -m unittest discover -s tests -p 'test_record*.py' -q`: **13 tests passed**, including three existing RecorderService tests and ten recording-space/error handling tests.
- `python -m compileall -q piserver tests`: passed in the local checkout.
- Both changed JS scripts passed V8 syntax parsing. Exact blob hashes for changed recorder and new helper/tests match the executed local files.
- The ControlService catch and API confirmation were added via unique source anchors on the **current PR #23 branch**; their Flask integration has not been tested locally.

## Known limits / next steps
- Flask is unavailable in the local test environment; full current branch API integration was not run. Real PiServer hardware motor/camera tests and SD-card power-loss behavior remain pending.
- PiServer JSONL append recovery is best-effort, not an atomic multi-file transaction; the user should inspect incomplete captures after an ENOSPC fault. Independent model upload and other filesystem writers are outside this guard.
- The sampling policy yields an occasional 2-second lag in session-size display. Low-space warning is exposed in API status rather than a new UI banner, preserving the accepted layout.
- Permission denial and mount disappearance also stop new recording writes but do not stop driving. A motor-side watchdog remains independent.
- Review/merge PR #23 first, following its earlier stacked dependencies. No full project ZIP or unrelated component changes.
