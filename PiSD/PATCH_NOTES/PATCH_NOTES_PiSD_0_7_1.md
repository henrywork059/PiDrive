# PiSD 0.7.1 Patch Notes

## Request summary
Update the PiSD steering algorithm so left/right input controls turn curve tightness while up/down input controls travel speed along that curve. Keep the old direct motor-speed mixer as a selectable fallback instead of removing it.

## Cause / root cause
The previous PiSD motor mapping used an arcade-style differential mixer:

```text
left = throttle - steer_mix * steering
right = throttle + steer_mix * steering
```

That makes steering directly add/subtract motor speed. At higher steering values it can quickly drive one side backward, causing pivot-like behaviour. This is harder to control manually and less clear for AI training because steering is mixed directly into motor output rather than representing a path/curve choice.

## Files changed
- `pisd/__init__.py`
- `config/defaults.json`
- `pisd/services/motor_service.py`
- `pisd/core/settings_manager.py`
- `pisd/web/templates/settings_tab.html`
- `pisd/web/static/js/settings_tab.js`
- `pisd/web/templates/testing_server.html`
- `docs/MOTOR_CALIBRATION.md`
- `docs/SETTINGS_MANAGER.md`
- `README.md`
- `scripts/test_settings_persistence.py`
- `scripts/test_motor_steering_modes.py`
- `PATCH_NOTES/PATCH_NOTES_PiSD_0_7_1.md`

## Exact behaviour changed
- Added motor steering mode selection:
  - `turn_rate` — new default curve/radius-feel algorithm.
  - `arcade_mix` — old PiSD mixer preserved as fallback.
- Added saved motor tuning values:
  - `steering_mode`
  - `turn_gain`
  - `turn_curve`
  - `min_inside_speed`
  - `allow_pivot_turn`
- Updated default motor settings so `steering_mode` is now `turn_rate`.
- In `turn_rate` mode:
  - throttle is treated as travel speed along the curve;
  - steering is treated as unitless curve tightness;
  - positive steering means a right curve;
  - negative steering means a left curve;
  - the outside wheel keeps requested speed;
  - the inside wheel slows based on `turn_gain` and `turn_curve`;
  - the inside wheel does not reverse by default.
- `allow_pivot_turn=false` keeps the new non-pivot behaviour by default.
- `allow_pivot_turn=true` can restore pivot-style behaviour for zero-throttle or very tight turns when deliberately enabled.
- Existing `left_direction`, `right_direction`, `steering_direction`, speed limits, biases, and `steer_mix` remain supported.
- `steer_mix` is now specifically the old `arcade_mix` fallback mixer control.
- Manual Drive and AI Mode both benefit because both already route final steering/throttle commands through `MotorService.update()`.
- The Settings page now exposes the new steering algorithm settings.
- The Testing Server page now exposes the same motor algorithm settings for safe API checks.
- Motor status and `last_command` now report the steering mode and turn-rate tuning values used for the last command.
- Updated docs to explain the new turn-rate algorithm and fallback behaviour.
- Updated `pisd.__version__` to `0.7.1`.

## Compatibility notes
- Existing `runtime_settings.json` files remain compatible. Missing new motor keys are filled from defaults.
- Existing motor direction calibration still applies after the new mapping.
- Existing `arcade_mix` behaviour can be restored by setting `steering_mode` to `arcade_mix`.
- No camera, overlay geometry, recording format, or AI model-loading behaviour was changed.
- The new algorithm is unitless; it does not require wheel radius, RPM, track width, or real-metre turning radius calibration.

## Rollback-risk checks
Reviewed the latest PiSD patch notes before editing:

- `0_7_0`: stable package built from accepted `0_6_1` through `0_6_7`.
- `0_6_7`: overlay settings recorded with screenshots/recordings for trainer redraw.
- `0_6_6`: popup overlay settings, unclamped overlay numbers, advanced overlay values.
- `0_6_5`: number inputs replacing sliders.

Confirmed this patch does not modify the shared overlay geometry, overlay popup, overlay setting persistence, recording metadata, camera defaults, AI model loading, or recording folder structure.

## Verification actually performed
- Started from clean `PiSD_0_7_0.zip`.
- `python3 -m compileall -q pisd scripts PiSD.py`
- `node --check pisd/web/static/js/settings_tab.js`
- `node --check pisd/web/static/js/manual_drive.js`
- `node --check pisd/web/static/js/ai_mode.js`
- `node --check pisd/web/static/js/overlay_geometry.js`
- `python3 scripts/test_motor_steering_modes.py`
- `python3 scripts/test_motor_service.py --duration 0.05 --throttle 0.18 --steering 0.35`
- `python3 scripts/test_settings_persistence.py`
- `python3 scripts/test_manual_drive_page.py --static-only`
- `python3 scripts/test_ai_mode_page.py --static-only`
- `python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui`

## Verification not performed
- Real Raspberry Pi motor hardware testing was not run in this container.
- Full Flask API endpoint tests were not run because Flask is not installed in this container. Attempting `python3 scripts/test_api_endpoints.py` reported that Flask must be installed from `requirements.txt` first.
- Real Manual Drive / AI Mode browser driving behaviour was not tested on the target Pi.

## Known limits / next steps
- Start hardware testing with wheels lifted and low throttle.
- If the car turns too wide, increase `turn_gain` gradually.
- If small steering feels too sensitive, increase `turn_curve` above `1.5`.
- If stopping the inside wheel makes the car drag or stall, raise `min_inside_speed` slightly.
- Keep `allow_pivot_turn=false` for normal training data unless pivot turns are specifically wanted.
