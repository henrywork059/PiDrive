# PiSD 0.7.3 Patch Notes — Motor Tuning Page + Overlay Match Calibration

## Request summary

Add a dedicated Motor Tuning page where the user can:

- run the car straight at a chosen speed for chosen seconds;
- run the car turning left or right at chosen speed/turn amount for chosen seconds;
- run a custom steering/throttle timed command;
- tune the motor `turn_rate` settings;
- tune the overlay on the same page so the visual predicted path can be matched to the real car turning motion.

This patch builds forward from `PiSD_0_7_0` plus accepted patches `0_7_1` and `0_7_2`.

## Cause / design issue

After `0_7_1` and `0_7_2`, the steering algorithm and overlay share the same turn-rate meaning, but calibration still had to be done across separate pages:

- motor steering settings were mainly in Settings / Testing pages;
- overlay settings were mainly in Manual Drive popup;
- there was no simple page that could run a repeatable timed motion and immediately tune the overlay against what the real car did.

This made it difficult to match the drawn visual path to the real turning radius.

## Files changed

- `PiSD/pisd/__init__.py`
  - Updated version to `0.7.3`.

- `PiSD/pisd/app.py`
  - Added `/motor-tuning` page route.
  - Added `/api/motor/tune-run` endpoint.
  - Added Motor Tuning page to the GUI manifest and shared presentation applies-to list.

- `PiSD/pisd/services/motor_service.py`
  - Added `run_timed_drive(...)` helper.
  - Timed tuning runs use the same `MotorService.update()` path as Manual Drive and AI Mode.
  - Timed tuning runs always request `stop()` in a `finally` path after the requested duration.

- `PiSD/pisd/web/templates/front_page.html`
  - Added a Motor Tuning card to the front page.

- `PiSD/pisd/web/templates/motor_tuning.html`
  - New dedicated Motor Tuning page.

- `PiSD/pisd/web/static/css/motor_tuning.css`
  - New responsive Motor Tuning page styling.

- `PiSD/pisd/web/static/js/motor_tuning.js`
  - New page logic for timed test commands, motor setting save/apply, overlay setting save/apply, and live overlay preview.

- `PiSD/scripts/test_motor_tuning_page.py`
  - New static/source-contract test for the Motor Tuning page and simulation timed-drive helper.

- `PiSD/docs/MOTOR_CALIBRATION.md`
  - Added Motor Tuning workflow notes.

- `PiSD/README.md`
  - Updated current version and added Motor Tuning workflow documentation.

## Behaviour changed

### New page

A new page is available at:

```text
/motor-tuning
```

It is linked from the front page.

### New timed motor test endpoint

A new endpoint is available at:

```text
POST /api/motor/tune-run
```

Expected request fields:

```json
{
  "steering": 0.5,
  "throttle": 0.18,
  "duration": 0.75,
  "label": "tune_turn_right",
  "safety_ack": true,
  "enable_motor_output": true
}
```

The endpoint:

1. clamps steering/throttle to `[-1.0, 1.0]`;
2. clamps duration to `0.05`–`10.0` seconds;
3. requires safety acknowledgement and motor-output enable on real hardware;
4. stops AI drive influence before the tuning command;
5. calls the normal motor update path;
6. waits for the selected duration;
7. sends STOP in a `finally` path.

### Motor tuning UI

The page includes:

- Straight travel test:
  - speed;
  - seconds;
  - forward/reverse buttons.

- Turn test:
  - left/right direction;
  - speed;
  - turn amount;
  - seconds.

- Custom command:
  - steering;
  - throttle;
  - seconds.

- Motor algorithm settings:
  - `steering_mode`;
  - `turn_gain`;
  - `turn_curve`;
  - `min_inside_speed`;
  - `steer_mix`;
  - `allow_pivot_turn`.

- Overlay matching settings:
  - `turn_rate_visual_scale` as the main visual match control;
  - curve strength / curvature scale / curvature limit;
  - path length and width;
  - road half width / wheelbase;
  - projection anchor and perspective settings;
  - turn compression / width taper;
  - sample count / opacity.

Saved overlay values continue to be stored under:

```text
manual_drive.overlay
```

So Manual Drive recordings/screenshots and future piTrainer redraw can use the same calibration.

## Compatibility notes

- The existing `turn_rate` steering algorithm from `0_7_1` is preserved.
- The old `arcade_mix` fallback is still available.
- The `0_7_2` overlay alignment is preserved; the new page uses the same shared `overlay_geometry.js` helper.
- Manual Drive and AI Mode files are not replaced or rolled back.
- Existing runtime config keys are preserved.

## Verification performed

Applied on a working tree built from clean `PiSD_0_7_0.zip` plus patches `0_7_1` and `0_7_2`, then checked:

```text
node --check pisd/web/static/js/motor_tuning.js
node --check pisd/web/static/js/overlay_geometry.js
node --check pisd/web/static/js/manual_drive.js
node --check pisd/web/static/js/ai_mode.js
python3 -m compileall -q pisd scripts PiSD.py
python3 scripts/test_motor_steering_modes.py
python3 scripts/test_motor_tuning_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_ai_mode_page.py --static-only
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
```

Also manually ran a simulation-only `MotorService.run_timed_drive(...)` check and confirmed the timed command stopped with final `last_left = 0.0` and `last_right = 0.0`.

## Verification not performed

- Real Raspberry Pi GPIO/motor hardware movement was not tested here.
- Full Flask route/API client test was not run because Flask is not installed in this container.
- Real browser/touchscreen layout was not tested.

## Known limits / next steps

- The overlay is still a pseudo-perspective projection, not a calibrated camera homography.
- The Motor Tuning page helps manually fit the overlay to observed motion, but it does not automatically estimate real turning radius from video or encoder data.
- A future patch could add measured calibration presets, left/right separate overlay correction, or a saveable calibration checklist.
