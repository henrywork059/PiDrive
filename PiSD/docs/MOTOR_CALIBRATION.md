# PiSD Motor Calibration and One-by-One Motor Tests

## Purpose

Different Pi cars may use different motor wiring, motor driver boards, pin assignments, and physical wheel orientation. Do not assume that the default left/right pins or direction multipliers are correct for every car.

PiSD 0.1.1 adds a safer one-by-one motor calibration path. It can test:

- left motor only
- right motor only
- raw direction 1
- raw direction 2
- multiple low speeds
- automatic stop after every step
- JSON summary output with PiSD error codes

## Direction meaning

For motor calibration, direction names are raw driver directions:

| Name | Meaning |
|---|---|
| `direction_1` | first/forward pin of that motor pair is active |
| `direction_2` | second/reverse pin of that motor pair is active |

This is intentionally separate from normal driving words like forward/reverse, because each car may be wired differently.

After testing, observe which raw direction makes each wheel move the real car forward. If a motor's forward direction is opposite of PiSD's normal drive direction, change that side's `left_direction` or `right_direction` to `-1` in a future config/persistence patch.

## Safe simulation test

Run this first. It does not move real motors.

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_motor_channels.py
```

Expected:

- each side/direction/speed is printed as JSON
- final code is `PISD-OK-000`
- final motor output is stopped

## Real GPIO channel test

Lift the wheels before running this.

```bash
cd ~/PiDrive/PiSD
python3 scripts/test_motor_channels.py --hardware --enable-motor-output
```

Without `--yes`, the script asks before each real movement. Type `RUN` only when the car is safe.

To run automatically after you are confident:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --yes
```

## Smaller or larger speed sweep

Start low:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --speeds 0.10,0.15,0.20 --duration 0.30
```

Use higher speeds only if the wheels are lifted and the low-speed tests are safe:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --speeds 0.20,0.35,0.50 --duration 0.30
```

## Test one side only

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --sides left
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --sides right
```

## Test one raw direction only

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --directions 1
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --directions 2
```

## Override pins for a car

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --left-pins 17,27 --right-pins 22,23
```

## Temporary logical direction test

Raw calibration ignores saved direction multipliers by default. To test the current logical direction multipliers too:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --apply-config-direction
```

Temporary direction override example:

```bash
python3 scripts/test_motor_channels.py --hardware --enable-motor-output --left-direction -1 --right-direction 1 --apply-config-direction
```

## Live API single-channel endpoint

A running PiSD server now exposes:

```text
POST /api/motor/test-channel
```

Example JSON:

```json
{
  "side": "left",
  "direction": 1,
  "speed": 0.15,
  "duration": 0.35,
  "enable_motor_output": true
}
```

When the server is hardware-enabled, this endpoint refuses real output unless `enable_motor_output` is true and reports `PISD-MOT-008`.

## Summary output

The script writes:

```text
PiSD/test_outputs/motor_channels/summary.json
```

Use this file to compare car setups and decide which direction multipliers or pin pairs should become the saved config.

## Manual Drive steering algorithm modes

PiSD 0.7.1 changed the default steering interpretation for normal drive commands. PiSD 0.8.1 removed `turn_gain` from real motor steering. PiSD 0.8.2 also removes motor `turn_curve`, so steering X linearly controls turn tightness while overlay calibration stays visual-only/manual.

The old mode is still available as `arcade_mix`:

```text
left = throttle - steer_mix * steering
right = throttle + steer_mix * steering
```

This can pivot or reverse one side quickly when steering is high. It is useful as a fallback because it matches older PiSD behaviour.

The new default mode is `turn_rate`:

```text
X / steering input = curve tightness
Y / throttle input = travel speed along that curve
```

In `turn_rate` mode, steering no longer means "add speed to one motor and subtract from the other" directly. Instead, steering produces a unitless turn value:

```text
turn = steering
turn_mag = abs(steering)
```

Then the inside wheel is slowed while the outside wheel keeps the requested travel speed:

```text
right curve: left = speed,                 right = speed * inside_factor
left curve:  left = speed * inside_factor, right = speed
```

With the default `allow_pivot_turn = false`, the inside wheel does not reverse. This gives a radius-feel control where the car travels along a curve rather than snapping into a spin.

Available motor settings:

| Setting | Meaning |
|---|---|
| `steering_mode` | `turn_rate` for the new curve/radius-feel control, or `arcade_mix` for the old mixer. |
| `min_inside_speed` | Minimum inside-wheel factor in non-pivot mode. Use this if the inside wheel stopping makes the car drag or stall. |
| `allow_pivot_turn` | Allows the inside wheel to reverse for very tight turns and zero-throttle pivoting. Default is `false`. |
| `steer_mix` | Used by `arcade_mix` fallback mode. It is kept for compatibility and calibration comparisons. |



### Intended output vs hardware output

PiSD 0.8.3 separates the output values shown to the driver from the signed PWM values sent to the motor driver. PiSD 0.8.4 keeps Manual Drive steering direct: drag-pad X is the steering value and no steer-strength multiplier is used.

- `last_intended_left` / `last_intended_right` are vehicle-motion intent values. Forward travel should show both sides as positive, even if one physical motor has `left_direction` or `right_direction` set to `-1`.
- `last_left` / `last_right` remain the hardware-applied values after direction multipliers. These are useful for wiring diagnostics.

The Manual Drive live overlay and Motor Tuning readout use the intended values, because they should describe how the car is intended to move. Hardware diagnostics remain available in the full motor status.

### Visual path overlay alignment

The Manual Drive and AI Mode path overlays keep visual matching separate from motor tuning. From PiSD 0.8.10, the Manual Drive `Manual visual tuning` popup exposes only seven user-facing visual controls without the earlier user-facing min/max caps: `turn_rate_visual_scale`, `path_length_scale`, `path_width_scale`, `base_y`, `horizon_y`, `perspective_scale`, and `opacity`. Deeper geometry values are internal renderer defaults. Changing overlay values changes only the drawn path; real motor steering stays linear.

Recommended Manual Drive overlay calibration order:

1. Use `Turn tightness`, `Path length`, and `Path width` to match the guide shape to the car path.
2. Use `Near Y`, `Horizon Y`, and `Perspective strength` to align the guide to the camera view.
3. Use `Opacity` only for visibility after the shape and camera anchors look correct.

When `steering_mode` is switched back to `arcade_mix`, the overlay keeps the older wheelbase/tan-style visual fallback so legacy mixer comparisons still make sense.

The Manual Drive overlay settings are visual-only. They control how strongly the path is drawn over the camera frame, but they do not change motor output.

Expected behaviour with default `turn_rate` mode:

| Input | Expected output feel |
|---|---|
| up only | straight forward |
| up + slight right | wide right curve |
| up + full right | tight right curve with right/inside wheel slowed |
| down + slight left | reverse along a left curve |
| left/right only | no pivot by default unless `allow_pivot_turn` is enabled |

## Error codes

| Code | Meaning |
|---|---|
| `PISD-MOT-007` | invalid motor channel test input |
| `PISD-MOT-008` | live API channel test was not armed with `enable_motor_output` |
| `PISD-MOT-009` | motor channel test output command failed |
| `PISD-TEST-007` | motor channel test script detected a failed step |

## PiSD 0.8.7 Motor Tuning page reset

`/motor-tuning` has been cleared in patch `0_8_7` so the calibration workflow can be rebuilt from a clean layout. The previous page panels for safety arming, timed motion, live preview, motor settings, overlay settings, and logs are no longer rendered.

This reset does not remove the backend motor behaviour:

- Linear X steering remains active in `MotorService`.
- The start dead-zone kick remains a hardware-output aid and does not change intended steering/throttle labels.
- Overlay tuning remains separate from real motor output.
- `/api/motor/tune-run` remains available for a future rebuilt UI or direct API checks.

Use Manual Drive and backend tests while the new tuning layout is being designed.
