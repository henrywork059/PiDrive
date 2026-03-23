# CustomDrive 0_1_9 Patch Notes

## Purpose
This patch adds a very small standalone PCA9685 servo test so the servo path can be verified independently from the manual-control app or autonomous runtime.

## Added
- `CustomDrive/run_servo_test_demo.py`
- `CustomDrive/custom_drive/servo_test.py`
- `CustomDrive/config/servo_test.json`

## What it does
- initializes a PCA9685 through `adafruit-circuitpython-servokit`
- tests one servo channel at a time
- supports `info`, `set`, `sweep`, and `release` modes
- prints clear errors when I2C is disabled, the library is missing, or the PCA9685 cannot be found

## Default test behavior
The default run performs a sweep on channel `0`:
- 40°
- 90°
- 115°
- 90°

for 3 cycles, then releases the channel.

## How to run on the Pi
From `~/PiDrive/CustomDrive`:

```bash
python -m pip install adafruit-circuitpython-servokit
python run_servo_test_demo.py --mode info
python run_servo_test_demo.py --mode sweep
```

To test a different channel:

```bash
python run_servo_test_demo.py --mode sweep --channel 1
```

To set a fixed angle:

```bash
python run_servo_test_demo.py --mode set --channel 0 --angle 90
```

To release PWM output:

```bash
python run_servo_test_demo.py --mode release --channel 0
```

## Notes
- Default PCA9685 address is decimal `64`, which is hex `0x40`.
- Servo power must come from the PCA9685 `V+` supply, not from the Pi 5V rail.
- If `sudo i2cdetect -y 1` does not show `40`, fix the wiring and I2C setup first.
