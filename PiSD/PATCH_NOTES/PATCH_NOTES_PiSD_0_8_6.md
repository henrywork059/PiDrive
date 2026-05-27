# PiSD 0.8.6 Patch Notes

## Request summary

This patch continues from `PiSD_0_8_5` and fixes the Motor Tuning page layout shown in the user's screenshot.

The requested change was that the Motor Tuning left live-preview panel was still taking too much desktop width and the left/right working areas should be equal width.

## Cause / root cause

`PiSD_0_8_5` added an equal-column rule in `motor_tuning.css`, but the page loads the shared layout CSS after the page-specific CSS. The later shared rule in `pisd_layout_system.css` still used a preview-dominant grid:

```css
grid-template-columns: minmax(var(--pisd-layout-preview-min), 1fr)
                       minmax(var(--pisd-layout-control-min), min(var(--pisd-layout-control-ideal), var(--pisd-layout-control-max)));
```

That made the live camera/overlay preview column receive extra width, while the safety/test column stayed narrower. The visible result was the screenshot issue: the left preview panel remained wider than the right control area even after the `0.8.5` page-specific rule.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/web/static/css/pisd_layout_system.css`
- `PiSD/scripts/test_motor_tuning_page.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_6.md`

## Behaviour changed

### Motor Tuning desktop grid is now truly equal width

The final shared layout rule for `/motor-tuning` now uses:

```css
grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) !important;
```

This applies after the shared layout CSS is loaded, so the browser's final effective grid becomes two equal halves on desktop:

```text
left half  = live camera frame + overlay visual match panel
right half = safety + timed motion tests
lower row  = motor settings + overlay settings
```

Responsive behaviour is preserved. Under the existing narrow-screen breakpoint, the page still stacks into one column.

## Preserved behaviour / rollback check

Reviewed the latest accepted PiSD patch line before finalising:

- `0_8_2`: linear X steering and removal of motor `turn_curve`.
- `0_8_3`: intended-output display separated from hardware-signed output.
- `0_8_4`: Manual Drive steer-strength removed and Motor Tuning preview compacted.
- `0_8_5`: motor start dead-zone kick, Motor Tuning page-specific equal-column attempt, and Manual-Drive-style tuning overlay.

Confirmed this patch does not roll back:

- Linear steering algorithm.
- Removal of `turn_gain` and motor `turn_curve`.
- Intended motor output display.
- Manual Drive steer-strength removal.
- Motor start dead-zone kick settings and hardware-layer kick behaviour.
- Live camera-backed Motor Tuning overlay preview.
- Manual-Drive-matched Motor Tuning overlay visual style.
- Compact Motor Tuning preview height.
- Back to Front Page header placement.

## Verification actually performed

Executed from the patched `PiSD` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/motor_tuning.js
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Motor Tuning static test now checks both `motor_tuning.css` and the later-loaded `pisd_layout_system.css`.
- The effective shared Motor Tuning layout rule contains `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)`.
- Existing compact preview, Back to Front Page header placement, and Manual-Drive-style overlay checks still passed.
- Existing settings persistence, motor steering, Manual Drive page, and standard validation checks passed.
- `PiSD.py --status-only` reports version `0.8.6`.

## Verification not performed / known limits

- Real Raspberry Pi browser layout was not tested in this container.
- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask browser-route tests were not run in this environment.

## Suggested Pi-side test sequence

1. Apply this patch after `PiSD_0_8_5_patch.zip`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/motor-tuning` on the same display/browser width used in the screenshot.
4. Confirm the left live-preview panel and the right safety/test panel each occupy half of the desktop page width.
5. Confirm the live preview still remains compact and the overlay still draws on top of the camera frame.
