# CustomDrive 0_4_5 Patch Notes

## Request summary
Fix the broken `0_4_4` Mission 1 stage-test patch forward from the current `CustomDrive_0_4_0` baseline plus the accepted `0_4_1` through `0_4_4` mission-stage patches.

Requested change:
- fix the `SyntaxError` in `mission1_stage_test.py` so the free-form CLI route runner can actually start on the Pi

## Anti-rollback review performed
Before patching, I checked:
- the real `CustomDrive_0_4_0` folder structure,
- the current `custom_drive/mission1_stage_test.py` state,
- the accepted recent mission-stage patch notes:
  - `PATCH_NOTES_CustomDrive_0_4_3.md`
  - `PATCH_NOTES_CustomDrive_0_4_2.md`
  - `PATCH_NOTES_CustomDrive_0_4_1.md`

That review was used to avoid rolling back:
- the standalone Mission 1 route-test runner,
- the corrected inverted right-turn default,
- the saved timing/config workflow added in `0_4_3`,
- and the existing isolated mission-stage path that does not disturb the main AI / arm / GUI systems.

## Root cause
The stage-test runner already supported:
- a fixed 3-leg route,
- CLI timing overrides for those 3 fixed legs,
- and config save-back.

But it still could not express a route with arbitrary repeated step order from the command line.

Using independent `append` lists for `--forward`, `--turn-right`, and `--turn-left` would have lost the original ordering typed by the user.
So the safer forward fix was to add a sequential route-step parser that records the step order exactly as `argparse` sees the flags.

## Files changed
- `CustomDrive/custom_drive/mission1_stage_test.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_4.md`

## Exact behavior changed

### 1) Added free-form ordered route steps to the CLI
The runner now supports repeated ordered route flags:
- `--forward SECONDS`
- `--turn-right SECONDS`
- `--turn-left SECONDS`

The order is preserved exactly as typed.

Example:
```bash
python3 run_mission1_stage_test_demo.py --mode live --forward 5 --turn-right 5 --forward 3 --turn-left 5
```

### 2) Added backward-compatible `route_steps` support in config
The config loader/saver now understands an optional `route_steps` list.

If `route_steps` is present and non-empty, it is used as the effective route.
If it is empty or missing, the runner still falls back to the existing legacy 3-leg timing fields:
- `forward_1_duration_s`
- `turn_right_duration_s`
- `forward_2_duration_s`

That keeps older configs and older commands working.

### 3) `--save-config` and `--run-and-save` now preserve free-form routes
If you pass ordered CLI route steps together with:
- `--save-config`, or
- `--run-and-save`,

the resolved ordered route is now written back to `config/mission1_stage_test.json` under `route_steps`.

### 4) Route summary output now reflects the effective sequence
The runner summary now prints:
- the effective route sequence,
- total duration,
- and the actual steering/throttle values for each resolved leg.

### 5) Preserved the previous fixed 3-leg tuning flow
The earlier fixed-leg route flow still works.

To avoid rolling back the `0_4_3` timing workflow, the patch keeps support for the earlier style:
- `--forward-1 ... --turn-right ... --forward-2 ...`

That compatibility path is preserved when the runner can clearly see you are using the older fixed 3-leg timing pattern.

## Verification actually performed
- Rebuilt the stage-test file forward from the current mission-stage patch state.
- Ran Python syntax checks.
- Ran:
  - `python3 -m compileall /tmp/cd044/CustomDrive/custom_drive/mission1_stage_test.py`
- Ran info checks for both legacy and free-form route modes.
- Ran a free-form CLI check with:
  - `--forward 5 --turn-right 5 --forward 3 --turn-left 5 --info`
- Verified the printed route order matched the typed order exactly.
- Ran a save-config check with free-form route steps and verified `route_steps` was written in order.

## Known limits / next steps
- This patch adds free-form route control to the CLI runner, not to the web GUI.
- Supported free-form actions in this patch are intentionally limited to:
  - `forward`
  - `turn-right`
  - `turn-left`
- If you later want `reverse`, `pause`, or one-click route presets in the GUI, that should be added as a separate focused patch.


## Exact bug fixed in 0_4_5
The `0_4_4` patch shipped a malformed f-string in `build_route(...)`:
- `f'step_{index:02d}_{action.replace('-', '_')}'`

Because the f-string itself used single quotes while the nested `replace('-', '_')` call also used single quotes, Python parsed it incorrectly and raised:
- `SyntaxError: f-string: unmatched "("`

This prevented the runner from importing at all on the Pi.

## Files changed in 0_4_5
- `CustomDrive/custom_drive/mission1_stage_test.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_5.md`

## Exact behavior changed in 0_4_5
- replaced the malformed inline f-string leg-name expression with a safe intermediate `leg_name` variable
- preserved the free-form ordered route CLI added in `0_4_4`
- preserved the legacy 3-leg timing compatibility added in `0_4_3`

## Verification actually performed for 0_4_5
- Ran Python syntax check on the patched file.
- Ran:
  - `python3 -m compileall /mnt/data/work045/CustomDrive/custom_drive/mission1_stage_test.py`
- Ran a direct import/execution smoke test with:
  - `PYTHONPATH=/mnt/data/customdrive_040/CustomDrive python3 -m custom_drive.mission1_stage_test --info` (using the patched file in place)
- Ran a free-form route info test with:
  - `--forward 2 --turn-right 6 --forward 4 --turn-right 6 --info`
- Verified the module imports successfully and the resolved route order matches the typed order.

## Known limits / next steps for 0_4_5
- This patch only fixes the broken import/syntax issue in the free-form mission-stage runner.
- It does not change the actual motor timings, steering direction, or live-drive backend behavior.
