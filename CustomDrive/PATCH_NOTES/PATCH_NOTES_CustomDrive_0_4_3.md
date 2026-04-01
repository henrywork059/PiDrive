# CustomDrive 0_4_3 Patch Notes

## Request summary
Patch the Mission 1 stage-test utility forward from the current `CustomDrive_0_4_0` baseline plus the accepted `0_4_1` and `0_4_2` mission-stage patches.

Requested change:
- make it easier to change the three route timings:
  - first forward time
  - turning time
  - second forward time

## Anti-rollback review performed
Before patching, I checked:
- the real `CustomDrive_0_4_0` folder structure,
- the accepted `0_4_1` Mission 1 stage-test addition,
- the accepted `0_4_2` timing/direction update,
- and recent existing CustomDrive notes in the baseline so this patch would stay isolated to the stage-test runner and not roll back AI, arm, or GUI behavior.

## Root cause / design issue
The current Mission 1 stage-test code already supported separate timing fields in JSON and separate CLI overrides:
- `forward_1_duration_s`
- `turn_right_duration_s`
- `forward_2_duration_s`

However, it was still inconvenient for repeated field tuning because there was no built-in way to save new CLI timing values back into `config/mission1_stage_test.json`.

That meant each retune session required either:
- editing the JSON manually, or
- rerunning the same full CLI overrides every time.

## Files changed
- `CustomDrive/custom_drive/mission1_stage_test.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_3.md`

## Exact behavior changed

### 1) Added config save support to the Mission 1 stage-test runner
A new `save_config(...)` helper was added so resolved stage-test settings can be written back to:
- `CustomDrive/config/mission1_stage_test.json`

### 2) Added `--save-config`
You can now save updated timing values without running the route:

```bash
python3 run_mission1_stage_test_demo.py --forward-1 6 --turn-right 5 --forward-2 6 --save-config
```

This updates the JSON file and exits.

### 3) Added `--run-and-save`
You can now save updated timing values and immediately run the route with them:

```bash
python3 run_mission1_stage_test_demo.py --mode live --forward-1 6 --turn-right 5 --forward-2 6 --run-and-save
```

### 4) Updated the runner text output
The route-start message now prints the actual resolved timing values instead of stale hardcoded text.

## Verification actually performed
- Rebuilt the stage-test files forward from the uploaded `CustomDrive_0_4_0` baseline and the accepted mission-stage patches.
- Ran Python syntax checks.
- Ran:
  - `python3 -m compileall custom_drive run_mission1_stage_test_demo.py`
- Ran:
  - `python3 run_mission1_stage_test_demo.py --info`
- Ran:
  - `python3 run_mission1_stage_test_demo.py --forward-1 7 --turn-right 4 --forward-2 8 --save-config`
- Verified the config file was rewritten with the new resolved timing values.

## Known limits / next steps
- This patch improves repeated field tuning from the runner, but it does not add a web UI for the stage-test route.
- If you want one-click controls for these three times inside the GUI later, that should be added as a separate focused patch.
