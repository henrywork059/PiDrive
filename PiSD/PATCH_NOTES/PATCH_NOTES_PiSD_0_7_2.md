# PiSD 0.7.2 Patch Notes

## Request summary
Patch the visualised path overlay so it follows the new PiSD `turn_rate` steering algorithm introduced in `0_7_1`, and review the overlay calculation for consistency with the updated steering meaning.

## Cause / root cause
`0_7_1` changed the motor interpretation so:

```text
steering = curve tightness / effective turn rate
throttle = travel speed along that curve
```

The shared overlay helper still generated its curve mainly from the older visual wheelbase / steering-angle approximation. That meant changing motor `Turn Gain` or `Turn Curve` changed the real wheel output, but the drawn path could still look like it was following the previous steering-angle model. The overlay could therefore diverge from the intended new control model, especially during stronger turns or after changing turn-rate settings.

## Files changed
- `pisd/__init__.py`
- `README.md`
- `docs/MOTOR_CALIBRATION.md`
- `pisd/app.py`
- `pisd/core/settings_manager.py`
- `pisd/web/static/js/overlay_geometry.js`
- `pisd/web/static/js/manual_drive.js`
- `pisd/web/static/js/ai_mode.js`
- `pisd/web/templates/manual_drive.html`
- `scripts/test_overlay_turn_rate_geometry.js`
- `scripts/test_settings_persistence.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_7_2.md`

## Exact behaviour changed
- The shared overlay helper now accepts motor steering settings as an input.
- In `turn_rate` mode, the overlay now uses the same unitless turn calculation as the motor service:

```text
turn_intent = sign(steering) * abs(steering) ** turn_curve * turn_gain
turn_intent = clamp(turn_intent, -1.0, 1.0)
```

- The overlay then maps that `turn_intent` into visual ground-plane curvature before applying the existing perspective projection, road-edge normal offset, fill corridor, and taper settings.
- Manual Drive now passes the latest motor steering settings from `/api/status` and `/api/control/manual` responses into the overlay helper.
- AI Mode now starts from the initial page motor settings and refreshes motor settings from `/api/ai/status`.
- `/api/ai/status` now includes the motor status so the AI overlay can stay aligned with the active `turn_rate` settings.
- Added a new visual-only Manual Drive overlay tuning value:
  - `turn_rate_visual_scale`
- `turn_rate_visual_scale` controls how strongly the unitless motor turn command is drawn. It does not change motor output.
- When motor `steering_mode` is switched back to `arcade_mix`, the overlay keeps the previous wheelbase/tan-style visual fallback so legacy comparisons still make sense.
- Overlay labels now show whether they are using `turn_rate` intent or arcade fallback.
- The existing reverse-guide-hidden behaviour is preserved.
- Existing overlay popup / numeric input behaviour from `0_6_6` is preserved.
- Existing overlay metadata recording from `0_6_7` is preserved; the new overlay setting is included through the existing overlay settings snapshot path.
- Updated `pisd.__version__` to `0.7.2`.

## Calculation review
Reviewed the current overlay pipeline after `0_7_1`:

1. Input command is still `steering` / `throttle`, not direct left/right motor output.
2. The old overlay calculation used a visual wheelbase and steering-angle conversion even though the motor algorithm now uses a unitless curve-tightness command.
3. Road edges were already correctly offset from local tangent normals before projection, so that part was kept.
4. The shared projection still uses the existing pseudo-perspective model with renderer safety bounds, so the patch did not replace the whole projection pipeline.
5. The core mismatch was the steering-to-curvature step, so this patch changes that step only and preserves the rest of the accepted road-corridor overlay design.

## Compatibility notes
- Existing saved runtime settings remain compatible.
- Existing overlay settings remain compatible. Missing `turn_rate_visual_scale` is filled from defaults.
- `turn_rate_visual_scale` is additive and visual-only.
- Existing recordings remain readable. New recordings will include `turn_rate_visual_scale` automatically when the current overlay settings are saved with capture/recording metadata.
- The motor algorithm itself is not changed by this patch.
- The old `arcade_mix` fallback remains available.

## Rollback-risk checks
Reviewed the latest PiSD patch notes before editing:

- `0_7_1`: new `turn_rate` motor steering algorithm and `arcade_mix` fallback.
- `0_7_0`: stable full v7 package built from accepted `0_6_1` through `0_6_7`.
- `0_6_7`: overlay settings recorded with screenshots/recordings for trainer redraw.
- `0_6_6`: popup overlay settings, unclamped numeric overlay values, and advanced overlay tuning values.

Confirmed this patch does not roll back:

- popup overlay settings;
- unclamped overlay value persistence;
- advanced overlay values;
- saved overlay metadata in recordings/screenshots;
- corrected left/right overlay direction;
- shared filled road-corridor overlay;
- new `turn_rate` motor output algorithm;
- old `arcade_mix` fallback;
- camera defaults;
- recording folder/data structure.

## Verification actually performed
- Started from clean `PiSD_0_7_0.zip` and applied `PiSD_0_7_1_patch.zip` before editing.
- `python3 -m compileall -q pisd scripts PiSD.py`
- `node --check pisd/web/static/js/overlay_geometry.js`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `node --check pisd/web/static/js/settings_tab.js`
- `python3 scripts/test_motor_steering_modes.py`
- `node scripts/test_overlay_turn_rate_geometry.js`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Real Raspberry Pi camera/motor hardware tests were not run in this container.
- Real browser/touchscreen overlay tuning was not tested on the target Pi.
- Full Flask API endpoint tests were not run in this container.

## Known limits / next steps
- Test with the actual car at low speed and wheels lifted first.
- If the overlay path still looks too flat after increasing motor `Turn Gain`, increase `turn_rate_visual_scale` in the Manual Drive overlay popup.
- If the car’s actual physical turn does not match the drawn path after motor tuning, adjust `turn_rate_visual_scale`, `curvature_scale`, `perspective_scale`, `base_y`, and `horizon_y` before changing deeper projection values.
- A future hardware-calibrated version could use measured wheelbase/track width or camera homography, but this patch intentionally keeps the current unitless PiSD tuning model.
