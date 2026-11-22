# CustomDrive 0_5_20 — U28 common safety API and explicit fault rearm

## Request
Provide the U28 schema-v1 safety status and fail-closed rearm for CustomDrive's standalone web controller and its separate real Mission 1 web runtime. Do not merge them into PiSD or PiServer.

## Root cause
A mission failure already stops motion in the U22 Mission 1 stage flow, but pressing Start again could reset failure state without an explicit operator acknowledgement. The generic web controller likewise allowed a failed runtime to be rebuilt/restarted without an externally visible safety-rearm contract.

## Files changed
- `custom_drive/mission1_session_app.py` — Mission 1 failure latch, explicit rearm, additive status/route, arm-movement guard; version 0_5_20.
- `custom_drive/web_app.py` — generic GUI web safety latch and API, fail-closed Start/Step and rebuild persistence.
- `custom_drive/mission1_web/templates/index.html` and `static/app.js` — small confirmed Rearm button.
- `custom_drive/web/templates/index.html` and `static/app.js` — confirmed Rearm button.
- `tests/test_u28_safety_contract.py` — isolated failure/rearm regression tests.
- `README.md` — operator flow; this patch note.

## Behavior
Add `safety` to the existing status (without changing its previous fields) and `GET /api/safety/status` / `POST /api/safety/rearm` with JSON `{"confirm":true}` on both CustomDrive web applications. Contract fields: `schema_version=1`, `component=CustomDrive`, `state`, `latched`, `motion_allowed`, `rearm_required`, `rearm_available`, `reason`. Fault rearm never starts motors automatically. Mission 1 failure remains latched after Stop; Start and manual arm role movement are refused until a checked worker-stop and motor stop finish. The generic web app retains a failed runtime latch across Reset/Rebuild/Run Settings; Start and Step reject until checked stop/reset. The operator sees a separate Rearm action.

## Compatibility / verification
Built atop draft PR #24 (0_5_19 U23 metrics), preserving #21 U22 stage outcomes and #11 U24 trigger overlays. No config keys or existing launchers change. Tests were added but **were not executed** against the fully stacked branch here; live Pi motor/camera/arm and GUI testing remain required. No claim of verified physical hardware stop is made.

## Limits
Safety status is local to each running application process, not a shared cross-process physical emergency-stop relay. Generic headless usage does not consume the web controller's process-local rearm latch; headless restart safety needs separate operational checks. No autonomous resume is triggered by rearm.
