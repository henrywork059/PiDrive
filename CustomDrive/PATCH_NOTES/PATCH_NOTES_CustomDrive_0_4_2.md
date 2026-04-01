# CustomDrive 0_4_2 Patch Notes

## Request summary
Patch the Mission 1 stage-test demo forward from the uploaded `CustomDrive_0_4_0` baseline plus the accepted `0_4_1` demo patch.

Requested changes:
- correct the stage-test route because left/right is currently inverted on the car,
- change the forward legs to **6 seconds** each,
- change the turn segment to **5 seconds**.

## Anti-rollback review performed
Before patching, I checked:
- the real `CustomDrive_0_4_0` folder structure,
- the accepted `0_4_1` Mission 1 stage-test patch,
- the previous recent CustomDrive notes already bundled in the baseline, including `0_3_10`, `0_3_9`, and `0_3_8`, so this route-only patch would not roll back the current arm, AI, or GUI behavior.

## Root cause / design issue
The first Mission 1 stage-test patch added the correct utility structure, but its default route was still tuned to the original short test request:
- forward 2s
- right turn 2s
- forward 2s

After real hardware testing, two field adjustments were needed:
1. the current steering direction on the car is inverted relative to the intended right-turn test, so the stage-test demo needed the opposite steering sign for the turn leg;
2. the next field stage now needs a longer route timing of **6s forward, 5s turn, 6s forward**.

This patch keeps the change tightly scoped to the stage-test demo and its config, rather than changing the wider drive or steering system.

## Files changed
- `CustomDrive/custom_drive/mission1_stage_test.py`
- `CustomDrive/config/mission1_stage_test.json`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_2.md`

## Exact behavior changed

### 1) Updated the default stage-test timing
The Mission 1 stage-test route now defaults to:
1. forward for **6.0s**
2. turn right for **5.0s**
3. forward for **6.0s**

### 2) Corrected the turn-leg steering sign for the current inverted steering behavior
The route still represents a **right-turn test**, but the default steering value used for that leg is now inverted so the physical car matches the intended right turn under the current hardware/runtime direction behavior.

Updated default:
- `turn_right_steering: -0.65`

### 3) Updated the stage-test text output
The route description and printed test sequence were updated so the runner now reports the new `6s -> 5s -> 6s` sequence instead of the old `2s -> 2s -> 2s` text.

## Verification actually performed
- Inspected the actual `CustomDrive_0_4_0` baseline and the accepted `0_4_1` Mission 1 stage-test files.
- Rechecked recent patch notes to avoid route-patch rollback into arm or AI work.
- Ran Python syntax checks.
- Ran:
  - `python3 -m compileall custom_drive run_mission1_stage_test_demo.py`
- Ran:
  - `python3 run_mission1_stage_test_demo.py --info`
- Verified the resolved route now reports a total of `17.00s` with:
  - forward leg 1 = `6.00s`
  - turn-right leg = `5.00s`
  - forward leg 2 = `6.00s`
- Verified the default turn-right steering value resolves to `-0.65`.

## Known limits / next steps
- I did not claim physical live-wheel validation inside this container.
- This patch intentionally changes only the Mission 1 stage-test utility defaults. It does not globally redefine steering direction for the entire project.
- If you later want the same inversion correction applied to other mission demos or the general drive stack, that should be patched separately after confirming the desired global direction convention.
