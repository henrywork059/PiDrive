# PiSD 0.8.9 Patch Notes

## Request summary

This patch continues from `PiSD_0_8_8` and updates the Manual Drive `Manual visual tuning` / `Overlay calibration` popup to match the reduced overlay-variable design.

The requested change was to update the Manual visual tuning Overlay calibration accordingly after reducing the Manual Drive overlay to a small set of user-facing visual controls.

## Cause / root cause

`PiSD_0_8_8` reduced the Manual Drive overlay settings down to seven visual controls, but the popup still felt like a plain number-entry list. The controls needed clearer grouping, clearer calibration guidance, and safer bounds so the page reflects the simplified overlay model.

## Files changed

- `PiSD/pisd/__init__.py`
- `PiSD/pisd/core/settings_manager.py`
- `PiSD/pisd/web/templates/manual_drive.html`
- `PiSD/pisd/web/static/css/manual_drive.css`
- `PiSD/pisd/web/static/js/manual_drive.js`
- `PiSD/docs/MOTOR_CALIBRATION.md`
- `PiSD/scripts/test_manual_drive_page.py`
- `PiSD/scripts/test_settings_persistence.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_8_9.md`

## Behaviour changed

### Manual visual tuning popup updated

The Manual Drive overlay calibration popup now presents the reduced seven controls as the intended calibration workflow:

1. `Shape`
   - Turn tightness
   - Path length
   - Path width
2. `Camera alignment`
   - Near Y
   - Horizon Y
   - Perspective strength
3. `Visibility`
   - Opacity

The popup title now makes the reduced scope explicit:

```text
Overlay calibration — 7 controls
```

The small summary beside the button now explains that these are seven visual-only overlay controls for matching the road guide to the live camera.

### Calibration guide added

A three-step guide is now shown in the popup:

```text
1. Set shape
2. Align camera position
3. Set visibility
```

This is intended to guide real-car overlay matching without mixing overlay settings with motor tuning.

### Bounded overlay inputs

The seven user-facing overlay controls now have practical UI bounds in the HTML inputs and matching backend/JS normalisation bounds:

- `turn_rate_visual_scale`: `0.10` to `6.00`
- `path_length_scale`: `0.35` to `2.50`
- `path_width_scale`: `0.05` to `1.20`
- `base_y`: `55` to `115`
- `horizon_y`: `5` to `80`
- `perspective_scale`: `0` to `140`
- `opacity`: `0.05` to `1.00`

`base_y` is also kept at least slightly below `horizon_y` so the overlay does not collapse into an inverted or unusable guide.

### Visual-only separation preserved

The popup wording and documentation now state more clearly that these controls only move the drawn road guide on the live camera view. They do not change:

- motor output
- linear X steering
- intended motor output labels
- AI training labels

## Compatibility / migration notes

- Existing `manual_drive.overlay` runtime settings remain loadable.
- Legacy advanced overlay keys are still pruned by the existing reduced-overlay normalisation.
- Out-of-range reduced overlay values are now clamped to practical visual ranges.
- The overlay schema version used by recordings remains `PiSD_0_8_8_overlay_settings_v2` because this patch changes the calibration UI and bounds, not the persisted seven-key schema shape.

## Preserved behaviour / rollback check

Reviewed the latest accepted PiSD patch line before finalising:

- `0_8_6`: Motor Tuning equal-width layout fix.
- `0_8_7`: Motor Tuning page reset/removal of all tuning panels.
- `0_8_8`: Manual Drive overlay reduced to seven visual-only controls.

Confirmed this patch does not roll back:

- Linear X steering.
- Removal of `turn_gain` from real motor steering.
- Removal of motor `turn_curve` from real motor steering.
- Manual Drive steer-strength removal.
- Intended motor output display.
- Motor start dead-zone kick backend/settings.
- Motor Tuning page reset from `0_8_7`.
- Manual Drive overlay reduced seven-key persisted schema from `0_8_8`.
- Manual Drive overlay remains visual-only and does not change motor output or recorded steering/throttle labels.

## Verification actually performed

Executed from the patched `PiSD/` folder:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_recording_service.py
node scripts/test_overlay_turn_rate_geometry.js
python3 scripts/test_motor_steering_modes.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

Observed key verification results:

- Manual Drive static test confirms the updated `Overlay calibration — 7 controls` popup, grouped Shape / Camera alignment / Visibility sections, and reduced bounded calibration logic.
- Settings persistence test confirms only the seven overlay controls plus `enabled` are saved and out-of-range values are clamped.
- Recording service test confirms the reduced overlay metadata schema is still recorded.
- Overlay geometry test confirms visual overlay scaling remains separate from real motor steering.
- Motor steering test confirms linear X steering and intended-output behaviour remain active.
- Standard validation passed in static/simulation mode.
- `PiSD.py --status-only` reports version `0.8.9`.

## Verification not performed / known limits

- Real Raspberry Pi camera preview was not hardware-tested here.
- Real Raspberry Pi motor movement was not hardware-tested here.
- Full Flask browser-route tests were not run because this container environment does not include Flask.

## Suggested Pi-side test sequence

1. Apply this patch after `PiSD_0_8_8_patch.zip`.
2. Start PiSD normally:

```bash
cd ~/PiDrive/PiSD
python3 PiSD.py --host 0.0.0.0 --port 5050 --hardware
```

3. Open `/manual-drive`.
4. Start the live camera stream.
5. Click `Manual visual tuning`.
6. Confirm the popup shows:
   - `Overlay calibration — 7 controls`
   - `Shape`
   - `Camera alignment`
   - `Visibility`
7. Adjust shape first, then camera alignment, then opacity.
8. Confirm the drawn overlay changes but the car's motor response remains the same direct linear X steering.
