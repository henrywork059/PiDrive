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

## Error codes

| Code | Meaning |
|---|---|
| `PISD-MOT-007` | invalid motor channel test input |
| `PISD-MOT-008` | live API channel test was not armed with `enable_motor_output` |
| `PISD-MOT-009` | motor channel test output command failed |
| `PISD-TEST-007` | motor channel test script detected a failed step |
