# PiSD 0.3.9 Patch Notes — Manual Control Range and Button Response Fixes

## Request summary

The user reported three Manual Drive issues after the previous patch:

- `Steer strength` still maxed out at `0.9`.
- The `Start` and `Live` camera buttons appeared to do the same thing.
- The top-bar `Refresh` and `STOP` buttons appeared to have no visible effect.

The user also asked to check that all button calls and responses are wired correctly.

## Cause / root cause

- The backend settings normalisation already allowed `steer_strength` up to `1.0`, but the Manual Drive HTML slider and Settings HTML slider still had `max="0.9"`.
- Older browser `localStorage` could keep the old `0.9` steering value after the HTML/backend was updated.
- `Start` previously started the camera and switched to live preview, while `Live` also switched to live preview. This made their roles unclear.
- Top-bar `Refresh` and `STOP` were calling API functions, but most feedback was only written into hidden/secondary log areas, making them look ineffective.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/templates/settings_tab.html`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/pisd/web/static/js/settings_tab.js`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_9.md`

## Exact behaviour changed

### Steering range/default

- Manual Drive `Steer strength` slider max is now `1.0`.
- Settings page `Steer strength` slider max is now `1.0`.
- Default manual steering strength is now `1.0` in the settings manager and Manual Drive page.
- Manual Drive now migrates the old browser-local `0.9` steer value back to the backend/default value instead of treating it as the new default ceiling.

### Camera button separation

- `Start camera` now starts the camera service and refreshes snapshot mode if the page is in snapshot mode.
- `Live stream` now starts the camera if needed and explicitly switches the preview to `/video_feed`.
- `Snapshot view` remains a still-frame refresh path through `/api/camera/frame.jpg`.

### Top-bar feedback

- `Refresh status` now refreshes status, updates the compact status text, refreshes file lists, and refreshes the snapshot frame when currently in snapshot mode.
- Top-bar `STOP` now recentres the drag pad, sends `/api/control/stop`, and updates the visible compact status line with the returned `PISD-*` code and message.
- Manual Drive writes important action feedback to the compact status line instead of relying only on the hidden action log.

### Button/API validation

- `scripts/test_manual_drive_page.py` now checks additional Manual Drive source contracts:
  - `Steer strength` max is `1.0`.
  - `Start camera`, `Live stream`, `Refresh status`, and short status feedback wiring exist.
- When Flask is available, the same script now also checks the key local API endpoints used by Manual Drive controls:
  - `/api/status`
  - `/api/camera/start`
  - `/api/camera/frame.jpg`
  - `/api/control/manual`
  - `/api/control/stop`
  - `/api/recording/status`
  - `/api/recording/items`
  - `/api/camera/stop`

## Verification actually performed

Local verification performed in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_responsive_layout_contract.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

## Not verified here

- Full Flask route/API execution because Flask is not installed in this packaging environment.
- Real Pi browser rendering.
- Real OV5647 camera stream switching.
- Real motor STOP/manual output on hardware.

These should be verified on the Raspberry Pi after applying the patch.

## Known limits / next steps

- Browser cache and old `localStorage` values can still affect what the user initially sees. Hard refresh the browser after patching.
- The patch intentionally changes only Manual Drive range/button feedback and does not alter motor output math, recording file structure, or responsive layout core rules.
