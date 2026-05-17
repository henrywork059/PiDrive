# PATCH NOTES - PiSD_0_4_5

## Request summary

- The overlay toggle still did not appear on the Manual Drive page after applying/pulling the previous patches.
- Make sure the 0_4_1 to 0_4_4 work remains included.
- Add the overlay button directly to the Manual Drive preview frame/page, because that is the page used for driving.

## Cause / root cause

The previous overlay work was implemented on the Main Dashboard camera preview. The Manual Drive page (`/manual-drive`) uses its own template, CSS, and JavaScript files:

- `pisd/web/templates/manual_drive.html`
- `pisd/web/static/css/manual_drive.css`
- `pisd/web/static/js/manual_drive.js`

Therefore, the Main Dashboard overlay button could exist correctly while still not appearing on the Manual Drive page.

## Files changed / included

This is a cumulative patch built forward from `PiSD_0_4_0` and includes the effective changed files from `0_4_1` through `0_4_4`, plus the Manual Drive overlay fix:

- `PiSD/pisd/__init__.py`
  - Version bumped to `0.4.5` for static asset cache-busting.
- `PiSD/pisd/core/settings_manager.py`
  - Preserves 0_4_1 cleanup.
- `PiSD/pisd/web/templates/main_dashboard.html`
  - Preserves Main Dashboard overlay and clarified camera button wording.
- `PiSD/pisd/web/static/css/main_dashboard.css`
  - Preserves Main Dashboard overlay styles.
- `PiSD/pisd/web/static/js/main_dashboard.js`
  - Preserves Main Dashboard intended-path overlay logic.
- `PiSD/pisd/web/templates/manual_drive.html`
  - Adds visible `Overlay: On` / `Overlay: Off` button to the Manual Drive Camera header.
  - Adds Manual Drive preview overlay markup inside `mdrvPreviewFrame`.
- `PiSD/pisd/web/static/css/manual_drive.css`
  - Adds Manual Drive overlay positioning, HUD, meters, path curve, car marker, and toggle button styles.
- `PiSD/pisd/web/static/js/manual_drive.js`
  - Adds Manual Drive overlay toggle behaviour.
  - Draws an intended path curve based on the current throttle and steering values.
  - Updates overlay values from Manual Drive drag commands, API responses, status refreshes, and STOP.
- `PiSD/scripts/test_main_dashboard.py`
  - Preserves previous Main Dashboard overlay checks.
- `PiSD/scripts/test_manual_drive_page.py`
  - Adds Manual Drive overlay contract checks.
- `PiSD/scripts/test_motor_channels.py`
  - Preserves previous cleanup.
- `PiSD/scripts/test_panel_testing_page.py`
  - Preserves previous cleanup.
- `PiSD/scripts/test_settings_persistence.py`
  - Preserves previous cleanup.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_1.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_2.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_3.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_4.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_5.md`

## Exact behavior changed

### Manual Drive page

- The Manual Drive Camera header now has a visible button:
  - `Overlay: On` when the overlay is visible.
  - `Overlay: Off` when the overlay is hidden.
- The overlay is drawn over the Manual Drive preview frame, not only the Main Dashboard preview.
- The overlay shows:
  - intended path curve,
  - mode label such as `STOPPED`, `FWD`, `REV`, `FWD LEFT`, or `FWD RIGHT`,
  - throttle value,
  - steering value,
  - left/right motor output values when available.
- Forward throttle draws the intended path upward.
- Reverse throttle draws the intended path downward with a dashed curve.
- Steering bends the curve left/right.
- STOP resets the overlay to zero/stopped.

### Main Dashboard page

- Existing 0_4_2 to 0_4_4 overlay and camera button wording are preserved.

## Compatibility notes

- No backend API route was changed.
- No motor mapping was changed.
- No camera service behaviour was changed.
- No saved runtime config is reset.
- This remains a client-side visual guide only. It does not draw onto saved JPEG/MJPEG frame bytes.

## Anti-rollback check

Confirmed the patch keeps recent accepted behaviour:

- 0_4_1 cleanup/commented-out unused code remains included.
- 0_4_2/0_4_3 Main Dashboard overlay and intended-path SVG logic remain included.
- 0_4_4 cumulative patch behaviour remains included.
- Manual Drive speed and steering limits still allow up to `1.0`.
- Manual Drive status still shows intended steering/throttle and actual left/right motor output.
- Manual Drive snapshot-view button remains removed.
- Recording/snapshot folder list, zip download, and delete controls remain unchanged.

## Verification actually performed

Performed locally in the extracted cumulative project:

```bash
python3 -m compileall -q .
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_main_dashboard.py --static-only
python3 scripts/test_front_page_tabs.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

All listed checks passed.

## Known limits / next steps

- Hardware camera/motor behaviour was not tested in this container.
- Browser rendering on the Pi still requires restarting PiSD and hard-refreshing the browser.
- If the button is still missing after this patch, check the URL: the Manual Drive page should be `/manual-drive`, and the static asset URL should include `v=0.4.5`.
