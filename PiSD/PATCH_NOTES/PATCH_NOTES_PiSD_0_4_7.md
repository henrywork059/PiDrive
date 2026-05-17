# PiSD_0_4_7 Patch Notes

## Request summary
- Implement the proposed next patch: overlay calibration and real control-state sync for the Manual Drive preview overlay.
- Make the overlay more trustworthy by showing whether it is using stopped state, manual intent, or live status.
- Add simple user-tunable overlay settings for path length, steering curve strength, opacity, and path width.
- Preserve the 0_4_1 through 0_4_6 cumulative fixes, including the Manual Drive overlay button and sampled predicted-arc overlay.

## Cause / root cause
- PiSD_0_4_6 improved the visual path shape, but the overlay was still fixed to hard-coded visual scale values.
- On a real car, camera angle, lens FOV, wheelbase, steering response, and user preference can make a single hard-coded overlay feel too long, too short, too curved, or too thick.
- The previous overlay displayed throttle/steering and motor values, but it did not explicitly show the source of the values. This could make it hard to know if the overlay was following immediate drag-pad intent, server status, or a stopped/reset state.

## Files changed / included
This is a cumulative patch built forward from `PiSD_0_4_0` and includes the effective changed files from `0_4_1` through `0_4_6`, plus the 0_4_7 changes.

New/updated in 0_4_7:

- `PiSD/pisd/__init__.py`
  - Version bumped to `0.4.7` for static asset cache-busting.
- `PiSD/pisd/core/settings_manager.py`
  - Adds persisted `manual_drive.overlay` defaults.
  - Safely normalises/clamps overlay calibration values on load/save.
  - Preserves older runtime settings and user-local config.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Adds a small live drive debug panel under the status strip.
  - Adds Manual Drive overlay calibration controls inside the Manual control panel.
- `PiSD/pisd/web/static/css/manual_drive.css`
  - Adds styling for the live debug panel.
  - Adds compact overlay calibration styling.
  - Adds data-source styling hooks for `live-status`, `manual-intent`, and `stopped` overlay states.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Adds overlay calibration loading, applying, and saving.
  - Adds nested local settings merge so overlay settings are not wiped when speed/steer settings are saved.
  - Uses calibration values in the predicted arc calculation:
    - path length scale changes visual horizon length,
    - curve strength changes steering curvature,
    - opacity changes overlay visibility,
    - path width changes the drawn path thickness.
  - Adds explicit overlay source tracking:
    - `stopped`,
    - `manual intent`,
    - `live status`.
  - Keeps STOP/reset from leaving stale old drag-pad values on the overlay.
- `PiSD/scripts/test_manual_drive_page.py`
  - Extends static checks for overlay calibration and live source debug tokens.
- `PiSD/scripts/test_settings_persistence.py`
  - Adds checks that overlay calibration settings are present and persisted.
  - Adds manager-level clamp checks for overlay calibration values.
- `PiSD/scripts/run_standard_validation.py`
  - Extends the Manual Drive static source contract to include overlay calibration/source-sync tokens.

Preserved cumulative files from previous patches:

- `PiSD/pisd/web/templates/main_dashboard.html`
- `PiSD/pisd/web/static/css/main_dashboard.css`
- `PiSD/pisd/web/static/js/main_dashboard.js`
- `PiSD/scripts/test_main_dashboard.py`
- `PiSD/scripts/test_motor_channels.py`
- `PiSD/scripts/test_panel_testing_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_1.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_2.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_3.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_4.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_5.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_6.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_7.md`

## Exact behavior changed

### Manual Drive overlay calibration
- Added a collapsible `Overlay calibration` section in the Manual control panel.
- User can tune:
  - `Path length`,
  - `Curve strength`,
  - `Opacity`,
  - `Path width`.
- These settings are saved under `manual_drive.overlay` through the existing settings API and local storage path.
- These settings affect only the visual overlay. They do not change motor commands or steering/throttle mapping.

### Overlay state/source sync
- Added a small debug row under the Manual Drive status strip showing:
  - overlay source,
  - steering,
  - throttle,
  - left motor output,
  - right motor output.
- Overlay source now shows one of:
  - `stopped` when steering/throttle and motor outputs are near zero,
  - `manual intent` while the drag pad is driving before/around the command send,
  - `live status` after server/status/API data is rendered.
- STOP resets the knob, command, motor output readout, overlay path, and overlay source to stopped before refreshing live status.
- Status refresh uses server motor status when available, but falls back to stopped if no live command exists and wheel outputs are zero.

### Settings safety
- Existing runtime config files are not reset.
- Older `runtime_settings.json` files without `manual_drive.overlay` are upgraded in memory with safe defaults.
- Bad overlay values are clamped rather than crashing:
  - path length scale: `0.5` to `1.8`,
  - curve strength: `0.4` to `1.8`,
  - opacity: `0.2` to `1.0`,
  - path width scale: `0.6` to `1.8`.

## Compatibility notes
- No backend route was renamed or removed.
- No motor output mapping was changed.
- No camera service behavior was changed.
- The overlay remains client-side visual guidance only. It is not written onto saved JPEG/MJPEG frames.
- This patch remains cumulative so it can be applied over a clean `PiSD_0_4_0` folder without needing separate 0_4_1 through 0_4_6 patch zips first.

## Anti-rollback check
Confirmed this patch keeps recent accepted behavior:

- 0_4_1 cleanup/commented-out unused code remains included.
- 0_4_2/0_4_3 Main Dashboard overlay and camera-control wording remain included.
- 0_4_4 cumulative patch behavior remains included.
- 0_4_5 Manual Drive overlay button remains in the Manual Drive page.
- 0_4_6 sampled predicted-arc overlay remains in use.
- Manual Drive speed and steering limits still allow up to `1.0`.
- Status still shows intended steering/throttle and actual left/right motor output.
- Snapshot-view button remains removed from the Manual Drive preview controls.
- Recording/snapshot folder list, zip download, and delete controls remain unchanged.

## Verification actually performed
Performed locally after applying the cumulative patch stack over a clean `PiSD_0_4_0` folder:

```bash
python3 -m compileall -q .
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-gui --skip-api --skip-camera --skip-motor
```

All listed checks passed.

Also attempted the full `python3 scripts/test_manual_drive_page.py` route check, but this container could not create the Flask app because Flask is not installed here (`PISD-APP-002`). Static/source validation was therefore used for the Manual Drive page in this environment.

## Known limits / next steps
- Hardware camera/motor behavior was not tested in this container.
- Overlay calibration defaults are visual starting points; they should be tuned while looking at the real camera angle on the car.
- The predicted path is still an approximate visualisation. It does not model wheel slip, real measured wheelbase, lens distortion, or exact steering geometry.
- After applying on the Pi, restart PiSD and hard refresh the browser so `v=0.4.7` static assets are loaded.
