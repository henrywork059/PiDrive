# PiSD 0.3.3 Patch Notes

## Request summary

The user reviewed the `0.3.2` GUI presentation in the browser and reported that the Manual Drive page still placed the Camera panel in the position intended for Manual Control, while the Manual Control drag-pad panel appeared lower on the page. The requested layout is:

- Status panel at the top.
- Camera panel directly under the status bar/panel.
- Manual Control panel in the right-side control position where the Camera panel was wrongly appearing.
- Keep the page unified and usable across PC/iPad-style screens.

## Cause / root cause

`0.3.1` introduced shared weighted/adaptive panel sizing and `0.3.2` added a global recovery stylesheet. However, the Manual Drive page could still be affected by earlier page-specific placement rules and saved presentation/adaptive settings. In browser testing, this allowed the Manual Drive panels to render in confusing columns even though the intended semantic order was status -> camera preview -> manual control/stop.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/css/unified_layout.css`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_ui_presentation_consistency.py`
- `PiSD/README.md`
- `PiSD/docs/TEST_PLAN.md`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_3_3.md`

## Exact behaviour changed

- Added a `manual-drive-page` body class so the Manual Drive page can be targeted by a stronger semantic layout recovery layer.
- Added a final `0.3.3` Manual Drive CSS override loaded through `unified_layout.css`.
- Locked Manual Drive PC/iPad layout to:
  - `status` in the upper main column
  - `preview` directly below `status`
  - `drive` in the right control column
  - `stop` below `drive`
  - `log` spanning the full page only when expanded
- Kept small-screen behaviour stacked in this order:
  - status
  - preview
  - drive
  - stop
  - log
- Kept the existing presentation settings for density, radius, panel gap, preview fit, button scale, console height, and role weights, but prevented them from moving the core Manual Drive panels into the wrong semantic positions.
- Updated tests so the Manual Drive source contract explicitly checks the recovered semantic layout.

## Compatibility notes

- No camera service code was changed.
- No motor service code was changed.
- No API endpoints were changed.
- No settings schema or saved settings format was changed.
- Existing browser-saved presentation settings remain compatible, but they should no longer break the Manual Drive panel placement.

## Verification performed

Performed locally in the packaging environment:

```bash
python3 -m compileall -q .
python3 PiSD.py --status-only
python3 scripts/check_error_reporting.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ui_presentation_consistency.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor
```

All checks passed.

## Known limits / next steps

- Real browser rendering on the Raspberry Pi/iPad/PC still needs to be visually checked by the user after applying the patch.
- This patch is layout-only. If the user wants finer per-device presentation presets later, the next patch should add explicit PC/iPad/phone layout presets in the Settings or Panel Presentation page.
