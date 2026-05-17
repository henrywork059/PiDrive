# PiSD 0.5.1 Patch Notes — Autopilot Mode Page

## Request summary

The user asked to add a new Autopilot mode page to allow autopilot.

This patch adds a real `/autopilot` browser page, a bounded backend `AutopilotService`, and safe API wiring for arm/start/stop/status. It builds forward from the uploaded stable reference baseline `PiSD_0_5_0.zip`.

## Baseline / anti-rollback check

Baseline used: `PiSD_0_5_0.zip`.

Before patching, the latest v5 package notes and recent v4 patch notes were checked so the accepted work was not rolled back:

- Manual Drive overlay toggle, predicted arc, overlay calibration, and debug/source display remain unchanged.
- Manual Drive STOP/status-refresh/fail-safe behavior remains unchanged.
- Preview FPS/stale-state reliability remains unchanged.
- Recording/snapshot folder management and backend path safety remain unchanged.

## Cause / root cause

PiSD had Manual Drive, Dashboard, Settings, Testing, and Panel pages, but no Autopilot mode page or dedicated backend state owner for autonomous/scripted movement.

Adding only a visual page would create unsafe/confusing behavior because the user could think autopilot exists while there is no backend start/stop/status path. Therefore this patch adds a service layer first.

The first autopilot implementation is deliberately conservative: it runs bounded scripted bench-test profiles, not camera/AI lane following. Camera/AI policy can be added later to this service without pretending it already exists.

## Files changed

- `PiSD/pisd/__init__.py`
  - Bumped version to `0.5.1` for static asset cache busting.
- `PiSD/pisd/core/errors.py`
  - Added autopilot error codes and test code.
- `PiSD/pisd/core/settings_manager.py`
  - Added safe persisted `autopilot` defaults and clamping.
- `PiSD/pisd/services/autopilot_service.py`
  - Added bounded scripted autopilot runtime service.
- `PiSD/pisd/app.py`
  - Added `/autopilot` route.
  - Added `/api/autopilot/status`, `/api/autopilot/config`, `/api/autopilot/start`, and `/api/autopilot/stop`.
  - Added autopilot status to `/api/status`.
  - Global STOP and Manual Drive commands now stop autopilot first before applying motor stop/manual output.
- `PiSD/pisd/web/templates/front_page.html`
  - Added Autopilot mode card.
- `PiSD/pisd/web/static/css/front_page.css`
  - Added Autopilot card styling.
- `PiSD/pisd/web/templates/autopilot.html`
  - Added Autopilot page UI.
- `PiSD/pisd/web/static/css/autopilot.css`
  - Added Autopilot page styling.
- `PiSD/pisd/web/static/js/autopilot.js`
  - Added Autopilot page browser logic and fail-safe stop.
- `PiSD/scripts/test_autopilot_page.py`
  - Added static/route contract test for the Autopilot page.
- `PiSD/scripts/test_autopilot_service.py`
  - Added simulation-mode AutopilotService behaviour test.
- `PiSD/scripts/test_front_page_tabs.py`
  - Added Autopilot card/static/route checks to front-page validation.
- `PiSD/docs/ERROR_CODES.md`
  - Documented new autopilot codes.
- `PiSD/README.md`
  - Noted the new `0.5.1` patch line and Autopilot page.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_5_1.md`
  - Added this patch note.

## Exact behavior changed

### New Autopilot page

A new page is available at:

```text
/autopilot
```

The front page now has an Autopilot mode card linking to it.

### Autopilot controls

The Autopilot page includes:

- safety acknowledgement checkbox;
- enable motor output checkbox;
- profile selector;
- max throttle slider;
- steer limit slider;
- steering bias slider;
- duration slider;
- update-rate slider;
- Save settings button;
- Start autopilot button;
- STOP autopilot buttons;
- live status/debug values;
- optional camera preview controls.

### Backend service

Added `AutopilotService` with these scripted profiles:

- `hold` — stopped / no motion;
- `straight_slow` — bounded slow straight movement;
- `gentle_s_curve` — bounded slow S-curve profile;
- `test_arc_left` — bounded left arc;
- `test_arc_right` — bounded right arc.

Current limits:

- throttle clamped to `0.0`–`0.35`;
- steer limit clamped to `0.0`–`0.75`;
- duration clamped to `1`–`60` seconds;
- tick rate clamped to `2`–`20` Hz.

### Safety behavior

- Autopilot starts only after safety acknowledgement.
- When hardware motor output is active, start also requires `enable_motor_output: true`.
- Autopilot automatically stops motors when it finishes, times out, or is stopped.
- Manual Drive commands stop the autopilot first before applying manual output.
- Global STOP stops the autopilot first before stopping motors.
- The browser page attempts a best-effort autopilot stop when leaving/reloading the page if autopilot is running.

### API behavior

New endpoints:

```text
GET  /api/autopilot/status
POST /api/autopilot/config
POST /api/autopilot/start
POST /api/autopilot/stop
```

The main `/api/status` payload now includes an `autopilot` section.

## Verification actually performed

Performed locally after applying changes to the uploaded `PiSD_0_5_0` baseline:

- `python3 -m compileall -q pisd scripts` — passed.
- `node --check pisd/web/static/js/autopilot.js` — passed.
- `node --check pisd/web/static/js/manual_drive.js` — passed.
- `python3 scripts/test_autopilot_service.py` — passed.
- `python3 scripts/test_autopilot_page.py --static-only` — passed.
- `python3 scripts/test_front_page_tabs.py --static-only` — passed.
- `python3 scripts/test_manual_drive_page.py --static-only` — passed.
- `python3 scripts/test_recording_service.py` — passed.
- `python3 scripts/test_settings_persistence.py` — passed.
- `python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor` — passed.

## Known limits / not verified

- Hardware motor behavior was not tested in this container.
- Real camera preview behavior on the Autopilot page was not tested in this container.
- Full Flask route checks were not completed because Flask is not installed in this container.
- This patch does not add camera-based AI lane following yet. It adds the page, service, API, safety gates, and bounded scripted autopilot profiles as the safe foundation.

## Apply

From the PiDrive parent folder:

```bash
cd ~/PiDrive
unzip -o PiSD_0_5_1_patch.zip
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

Then hard refresh the browser with `Ctrl + F5` so the `v=0.5.1` static assets are loaded.
