# CustomDrive 0_4_1 Patch Notes

## Request summary
Add the next Mission 1 test stage on top of the current `CustomDrive_0_4_0` baseline.

Requested behavior:
- provide a simple demo for field testing,
- drive **forward for 2 seconds**,
- then **turn right for 2 seconds**,
- then **drive forward for 2 seconds**.

The patch needed to be built forward from the current uploaded version and checked against recent accepted CustomDrive changes so it would not accidentally roll back the current arm, AI, or GUI work.

## Anti-rollback review performed
Before patching, I checked:
- the real file layout in the uploaded `CustomDrive_0_4_0.zip`,
- the latest available CustomDrive patch note in the archive: `0_3_10`,
- the previous three related notes: `0_3_9`, `0_3_8`, and `0_3_7`.

That review was used to avoid rolling back:
- the current direct-servo arm control path,
- the AI deploy / stop / overlay work,
- the existing mission controller and runtime flow,
- the current entry points and folder structure.

## Root cause / design issue
The current project already had:
- the full mission runtime,
- a timed route follower,
- and several standalone hardware test utilities.

But it did **not** yet have a dedicated, minimal Mission 1 route-test runner for the new field stage.

Trying to force this small field-path check into the full pickup/drop mission controller would add unnecessary risk because the full mission flow still includes:
- perception,
- target/drop-zone states,
- and pickup/release transitions.

For this stage, the safer forward change was to add a **standalone route-test demo** that reuses the current drive backend path without changing the main mission state machine.

## Files changed
- `CustomDrive/custom_drive/mission1_stage_test.py` **(new)**
- `CustomDrive/run_mission1_stage_test_demo.py` **(new)**
- `CustomDrive/config/mission1_stage_test.json` **(new)**
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_0_4_1.md`

## Exact behavior changed

### 1) Added a dedicated Mission 1 stage-test runner
A new standalone runner was added:
- `run_mission1_stage_test_demo.py`

This is a small route-test utility, not a replacement for the main mission runtime.

It performs the requested sequence:
1. forward for 2 seconds
2. right turn for 2 seconds
3. forward for 2 seconds

### 2) Added a reusable route-test module
A new module was added:
- `custom_drive/mission1_stage_test.py`

This module:
- loads a small JSON config,
- builds the 3-leg timed route,
- reuses `TimedRouteFollower`,
- reuses the existing `PiCarRobotBridge`,
- supports both `sim` and `live` modes,
- applies saved live motor settings from `CustomDrive/config/runtime_settings.json` when running in live mode.

### 3) Added a separate JSON config for this test stage
A new config file was added:
- `config/mission1_stage_test.json`

Default values are:
- mode: `sim`
- forward leg 1: `2.0s`
- right turn leg: `2.0s`
- forward leg 2: `2.0s`
- forward throttle: `0.28`
- right-turn throttle: `0.22`
- right-turn steering: `0.65`

This keeps the test route easy to retune later without editing Python code.

### 4) The live test path uses the real saved motor configuration
When run in `live` mode, the new test runner:
- imports PiServer's `MotorService`,
- applies the saved motor config from `runtime_settings.json`,
- sends commands through `PiCarRobotBridge`,
- stops the motors cleanly at the end or on shutdown.

That means this test follows the same motor-direction / bias settings path already used elsewhere in CustomDrive.

### 5) The main mission controller was intentionally left unchanged
This patch does **not** alter:
- `mission_controller.py`
- the normal pickup/drop mission state machine
- the current GUI/manual-control path
- the current AI pipeline

That was deliberate to keep this Mission 1 route test isolated and low-risk.

## Verification actually performed
- Inspected the actual `CustomDrive_0_4_0` folder layout and current entry points.
- Re-read the latest recent patch notes listed above before editing.
- Ran Python syntax checks on the new runner/module.
- Ran:
  - `python3 -m compileall custom_drive run_mission1_stage_test_demo.py`
- Ran:
  - `python3 run_mission1_stage_test_demo.py --info`
- Ran the new stage test in `sim` mode and verified the leg order:
  - forward leg 1
  - turn right leg
  - forward leg 2
- Verified the route total resolved to `6.00s` with the requested `2s + 2s + 2s` structure.

## Known limits / next steps
- I did **not** claim live wheel-motion validation in this container.
- The default config keeps `mode = sim` for safety. To test on the Pi, change it to `live` in `config/mission1_stage_test.json` or pass `--mode live` on the command line.
- The right-turn leg currently uses **steering + forward throttle**, not a stationary pivot. If you later want an in-place turn-style test instead, that should be a follow-up config or route change.
- This patch adds the requested demo stage, but it does not yet wire Mission 1 stage presets into the main GUI. That can be added later if you want one-click test-stage launching from the web UI.
