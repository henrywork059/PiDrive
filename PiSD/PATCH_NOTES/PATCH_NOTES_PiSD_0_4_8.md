# PiSD_0_4_8 Patch Notes

## Request summary

Build the next PiSD patch after `0_4_7` to improve Manual Drive safety and command consistency.

The requested focus was:

- keep one clear source of truth for the Manual Drive command state;
- audit STOP behavior so the visual state and motor output return to zero together;
- make Refresh status non-invasive;
- keep Start camera, Live stream, STOP motors, and Refresh status meanings separate;
- add a fail-safe stop when the Manual Drive page is left while movement is active.

## Baseline / rollback check

This is a cumulative patch built forward from `PiSD_0_4_0` and preserves the effective changes from `0_4_1` through `0_4_7`.

Before changing files, the recent Manual Drive patch notes were checked conceptually against the current code so the following accepted features were not rolled back:

- `0_4_5`: Manual Drive overlay toggle appears on the Manual Drive page, not only Dashboard.
- `0_4_6`: sampled predicted-arc overlay remains in use.
- `0_4_7`: overlay calibration and live debug/source panel remain in use.

## Cause / root cause

The main coding-level conflict found was in the Manual Drive Refresh behavior.

`refreshStatus(true)` previously refreshed the snapshot preview when the page was in snapshot mode. The snapshot image uses `/api/camera/frame.jpg`, and that endpoint may auto-start the camera when no frame exists yet. This meant a button labelled Refresh status could indirectly touch the camera path.

The command state was also spread across `lastPayload`, `lastMotorOutput`, overlay render calls, and status/API response render helpers. It worked, but it made future safety checks harder because different UI parts could be updated from different helper paths.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_8.md`

This cumulative patch zip also includes the prior changed files and patch notes from `0_4_1` through `0_4_7` so it can be applied over a clean `PiSD_0_4_0` folder.

## Exact behavior changed

### 1. Manual Drive command state is centralised

Added a small Manual Drive client-side state layer:

- `STOP_COMMAND`
- `STOP_OUTPUT`
- `normaliseManualCommand(...)`
- `normaliseMotorOutput(...)`
- `driveStateIsMoving(...)`
- `setDriveState(...)`
- `setStoppedDriveState(...)`

The drag pad, API response handler, status refresh handler, overlay, status strip, and debug panel now pass through the same state update path.

This keeps these displays aligned:

- drag pad readout;
- intended steering/throttle strip;
- left/right motor output strip;
- overlay path;
- overlay HUD/debug panel.

### 2. STOP behavior is clearer

STOP now immediately performs a local visual stop before waiting for the API response:

- knob returns to center;
- intended command becomes steering `0`, throttle `0`;
- left/right output display becomes `0`;
- overlay source becomes stopped;
- overlay path falls back to stopped/neutral state.

When `/api/control/stop` returns, the page reconciles with the backend motor status.

Button text/tooltips were clarified:

- top-bar button now says `STOP motors`;
- drag-pad stop button now says `STOP motors`;
- big stop remains `STOP ALL MOTORS`.

These controls stop motor output only. They do not stop the camera/live stream.

### 3. Refresh status is now status-only

`refreshStatus(true)` no longer calls `snapshotView()` and therefore no longer fetches `/api/camera/frame.jpg`.

Refresh status now:

- reads `/api/status`;
- updates visible status/motor/overlay values from backend status;
- refreshes recording/snapshot folder lists;
- leaves camera preview mode untouched;
- does not call camera start;
- does not send manual motor commands;
- does not send motor stop.

### 4. Start / Live / STOP / Refresh meanings are separated

Manual Drive button meanings are now clearer in markup/tooltips and JS behavior:

- `Start camera`: starts camera service and refreshes a snapshot frame.
- `Live stream`: starts camera if needed and switches the image to MJPEG stream.
- `STOP motors`: sends motor stop and clears movement/overlay state.
- `Refresh status`: refreshes status/file lists only.

### 5. Page unload fail-safe stop added

Added `sendFailSafeStop(...)`.

If movement is active and the user leaves, reloads, hides, or closes the Manual Drive page, the page attempts to send `/api/control/stop` using:

- `navigator.sendBeacon(...)` when available;
- `fetch(..., keepalive: true)` as a fallback.

Events wired:

- `pagehide`
- `beforeunload`
- `visibilitychange` when hidden

The fail-safe is guarded so it does not repeatedly spam stop requests when the car is already stopped.

## Verification actually performed

Performed locally after applying over a clean `PiSD_0_4_0` folder plus the cumulative changes:

- `python3 -m compileall -q .` passed.
- `node -c pisd/web/static/js/manual_drive.js` passed.
- `python3 scripts/test_manual_drive_page.py --static-only` passed.
- `python3 scripts/test_main_dashboard.py --static-only` passed.
- `python3 scripts/test_front_page_tabs.py --static-only` passed.
- `python3 scripts/test_settings_persistence.py` passed.
- `python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor` passed.

## Known limits / next steps

- Hardware motor behavior was not tested in this container.
- Full Flask route tests were not run here because this container environment does not include the same Pi runtime dependencies.
- The unload fail-safe uses browser best-effort delivery; this is safer than doing nothing, but browser page-unload requests are never a perfect real-time emergency-stop system.
- A future patch could add a backend command watchdog timeout, so the Pi stops motors automatically if no fresh Manual Drive command arrives within a short time.

## Apply

From the PiDrive parent folder:

```bash
cd ~/PiDrive
unzip -o PiSD_0_4_8_patch.zip
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard refresh the browser with `Ctrl + F5` so the `v=0.4.8` static assets are loaded.
