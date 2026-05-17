# PATCH NOTES - PiSD_0_4_4

## Request summary
- Rebuild the PiSD 0_4_1 through 0_4_3 changes into a single cumulative patch because the overlay toggle was not visible on the Pi after pulling/updating.
- Keep the previous cleanup and overlay work, but make the overlay toggle easier to find.
- Continue the PiSD 0_4_x patch line and use the simple patch zip name format.

## Cause / root cause
- The earlier 0_4_2 and 0_4_3 zip files were patch-only overlays. If the Pi folder did not already contain every 0_4_1 change, applying only the later small patch could leave the local project in a mixed state.
- The overlay toggle existed in the 0_4_3 template, but it was placed in the camera control button row under the preview frame. On narrower layouts or partially patched files, this made it easy to miss or fail to appear.

## Files changed / included
This patch is intentionally cumulative from the 0_4_0 baseline and includes the effective changed files from 0_4_1, 0_4_2, 0_4_3, plus this 0_4_4 fix:

- `PiSD/pisd/__init__.py`
  - Bumped runtime version to `0.4.4` so static asset URLs cache-bust correctly.
- `PiSD/pisd/core/settings_manager.py`
  - Preserves the 0_4_1 cleanup/settings-manager changes.
- `PiSD/pisd/web/templates/main_dashboard.html`
  - Preserves the preview overlay markup.
  - Moves the overlay toggle into the Camera Preview header as `Overlay: On` / `Overlay: Off` so it is visible immediately at the top of the preview panel.
  - Keeps Start camera + live / Stop camera only / Show live stream wording separated.
- `PiSD/pisd/web/static/css/main_dashboard.css`
  - Preserves overlay drawing styles.
  - Adds header action styling and clearer overlay-toggle styling.
- `PiSD/pisd/web/static/js/main_dashboard.js`
  - Preserves the intended-path overlay drawing logic from steering/throttle values.
  - Updates the toggle label and state marker to match the clearer header button.
- `PiSD/scripts/test_main_dashboard.py`
  - Extends static contract checks for the header overlay toggle and intended-path overlay.
- `PiSD/scripts/test_motor_channels.py`
  - Preserves the 0_4_1 motor-channel test cleanup.
- `PiSD/scripts/test_panel_testing_page.py`
  - Preserves the 0_4_1 panel-testing validation cleanup.
- `PiSD/scripts/test_settings_persistence.py`
  - Preserves the 0_4_1 settings-persistence validation cleanup.
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_1.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_2.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_3.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_4_4.md`

## Exact behavior changed
- The overlay toggle is now shown in the Camera Preview panel header, not hidden among the lower camera buttons.
- The toggle reads:
  - `Overlay: On` when the intended-path overlay is visible.
  - `Overlay: Off` when it is hidden.
- The preview overlay still draws the intended path from current throttle and steering values:
  - forward path draws upward,
  - reverse path draws downward with a dashed path,
  - steering bends the path left/right,
  - car icon rotation follows steering.
- The Camera Preview buttons remain semantically separated:
  - `Start camera + live` starts the camera service and switches the preview to MJPEG live stream,
  - `Stop camera only` stops the camera service only,
  - `Show live stream` reloads/switches the preview image source to the live stream only,
  - red `STOP` buttons stop motor output.

## Verification actually performed
Performed locally in the extracted cumulative project:

- `python3 -m compileall -q .`
- `python3 scripts/test_main_dashboard.py --static-only`
- `python3 scripts/test_front_page_tabs.py --static-only`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_motor_channels.py` in simulation mode only
- `python3 scripts/test_panel_testing_page.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor`

All listed checks passed.

## Known limits / next steps
- Hardware camera/motor behavior was not tested in this container.
- Flask route/browser rendering was not fully tested here beyond static validation because the Pi runtime environment is different from this container.
- After applying this patch on the Pi, restart PiSD and hard refresh the browser. Because version is bumped to `0.4.4`, static JS/CSS URLs should cache-bust, but the HTML template still requires the server to be restarted.
