# PiSD 0.9.1 Patch Notes

## Request summary

This patch updates the current `PiSD_0_9_0` stable v9 baseline with two Manual Drive changes:

1. Add a Manual Drive popup button above **Manual visual tuning** so the user can set the motor start dead-zone kick values directly from the driving page.
2. Change keyboard left/right steering so releasing the arrow key returns steering back to centre over 0.5 seconds instead of leaving the last steering value held.

## Cause / root cause

- The motor start dead-zone kick backend already existed from the accepted `0_8_5` work, but Manual Drive did not expose a compact page-level control for `start_deadzone` and `start_kick_seconds`. The user would otherwise need to use the wider Settings page.
- Keyboard steering added in `0_9_0` ramped while left/right was held, but releasing the key stopped the ramp loop and left the last steering value in place. That made keyboard steering behave like a latch instead of returning naturally to straight.

## Files changed

- `PiSD/pisd/__init__.py`
  - Updated package version to `0.9.1`.

- `PiSD/pisd/web/templates/manual_drive.html`
  - Added **Motor start dead-zone** button above **Manual visual tuning**.
  - Added `Motor dead-zone kick` popup with:
    - `Start dead-zone`
    - `Kick seconds`
    - `Reset to off`
    - `Apply motor start tuning`
  - Updated keyboard hint to say left/right release returns to 0.

- `PiSD/pisd/web/static/js/manual_drive.js`
  - Added Manual Drive motor start tuning popup wiring.
  - Loads existing motor `start_deadzone` and `start_kick_seconds` from runtime settings.
  - Applies values through `/api/motor/apply`, so the values are saved and applied to the real `MotorService` without moving the car.
  - Keeps intended motor output and AI labels unchanged by the temporary start kick.
  - Changed keyboard left/right release behaviour: when neither left nor right is held, steering ramps back to `0.00` over the same 0.5-second steering scale and sends a final centred command.
  - Keeps Space as full stop.

- `PiSD/pisd/web/static/css/manual_drive.css`
  - Added styling for the Manual Drive motor start tuning block so it matches the existing popup/panel style but is visually distinct from overlay visual tuning.

- `PiSD/scripts/test_manual_drive_page.py`
  - Updated static contract checks for the new motor start tuning popup.
  - Updated keyboard contract checks for release-to-centre behaviour.

- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_9_1.md`
  - Added this patch note.

## Behaviour changed

### Manual Drive motor start dead-zone popup

Manual Drive now has a button directly above **Manual visual tuning**:

```text
Motor start dead-zone
```

The popup controls:

```text
Start dead-zone  = temporary output used only when a wheel starts moving from rest
Kick seconds     = how long the temporary output is held
```

Example:

```text
start_deadzone = 0.20
start_kick_seconds = 0.12
```

If the intended motor command starts from rest at `+0.08`, PiSD briefly sends hardware output `+0.20`, then returns to `+0.08` after `0.12 s`.

The intended output/label remains `+0.08`; only the temporary hardware PWM is boosted.

### Keyboard steering return-to-centre

Keyboard control now behaves as:

```text
Hold Left/Right  -> steering ramps toward -1/+1 over 0.5 s
Release key      -> steering ramps back to 0 over 0.5 s
Space            -> stop motors and clear keyboard throttle/steering
```

The final centred command is force-sent so the backend does not remain on a previous non-zero steering value because of the Manual Drive send interval.

## Compatibility / migration notes

- Existing saved `motor.start_deadzone` and `motor.start_kick_seconds` values are preserved.
- Default remains unchanged:

```text
start_deadzone = 0.0
start_kick_seconds = 0.12
```

So existing users see no start-kick effect until they set `start_deadzone` above zero.

- The linear steering algorithm from `0_8_2` is preserved.
- Removed `turn_gain`, removed motor `turn_curve`, intended motor output display, overlay setting files, and stable `0_9_0` keyboard throttle behaviour are not rolled back.

## Verification actually performed

Performed locally in the container after patching `PiSD_0_9_0`:

```bash
python3 -m compileall -q pisd scripts PiSD.py
node --check pisd/web/static/js/manual_drive.js
python3 scripts/test_manual_drive_page.py --static-only
python3 scripts/test_settings_persistence.py
python3 scripts/test_motor_steering_modes.py
python3 scripts/run_standard_validation.py --skip-api --skip-camera --skip-motor --skip-gui
python3 PiSD.py --status-only
```

All checks above passed. I also tested applying `PiSD_0_9_1_patch.zip` over a clean `PiSD_0_9_0.zip` extraction and reran the same static/simulation validation successfully.

Attempted full Manual Drive Flask route test:

```bash
python3 scripts/test_manual_drive_page.py
```

The static checks passed, but the route check could not run because Flask is not installed in this container environment:

```text
PISD-APP-002: Flask is not installed. Run: python -m pip install -r requirements.txt
```

## Hardware testing

Hardware camera/motor testing was not run in this environment.

## Known limits / next steps

- The motor start kick still needs real car tuning to find the lowest reliable `start_deadzone` and shortest useful `start_kick_seconds`.
- If the motor jumps too much, lower `start_deadzone` first, then lower `start_kick_seconds`.
- If the motor still cannot start from low values, increase `start_deadzone` gradually.
