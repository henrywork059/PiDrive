# CustomDrive 0_1_10 Patch Notes

## Request summary
Add a new standalone servo demo that controls servo channels 1 and 2 together with one command. For now, both servos should rotate in the same direction.

## Cause / context
The previous servo tester verified one channel at a time. After confirming a single servo works, the next hardware step is a simple paired-channel test that can move two servos together without going through the main CustomDrive manual-control stack.

## Files changed
- `CustomDrive/custom_drive/dual_servo_test.py`
- `CustomDrive/run_dual_servo_test_demo.py`
- `CustomDrive/config/dual_servo_test.json`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_1_10.md`

## Exact behavior changed
- Added a standalone dual-servo tester for PCA9685.
- Default test channels are `1` and `2`.
- One command can now:
  - print config info
  - set both servos to one angle
  - sweep both servos together
  - release both channels
- Current default behavior drives both channels in the same direction using the same angle value.
- An optional opposite-direction mode is present for later testing, but the default config and normal use keep both channels moving together.

## How to run
From `CustomDrive`:

```bash
python3 run_dual_servo_test_demo.py --mode info
python3 run_dual_servo_test_demo.py --mode set --angle 90
python3 run_dual_servo_test_demo.py --mode sweep
python3 run_dual_servo_test_demo.py --mode release
```

Useful overrides:

```bash
python3 run_dual_servo_test_demo.py --mode sweep --channel-a 1 --channel-b 2
python3 run_dual_servo_test_demo.py --mode set --angle 120
```

## Verification actually performed
- Added the new files onto the current uploaded PiDrive tree.
- Ran `python -m compileall CustomDrive` successfully.
- Checked the new config defaults point to channels 1 and 2 and same-direction mode.

## Known limits / next steps
- This patch only verifies paired servo output, not arm linkage logic.
- If one servo is mounted reversed, switch to `--opposite-direction` or change the linkage orientation later.
- Real angle ranges may still need tuning per servo and linkage.
