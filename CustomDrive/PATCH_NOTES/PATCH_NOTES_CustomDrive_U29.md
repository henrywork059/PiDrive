# CustomDrive U29 — Deterministic synthetic mission replay

## Request and goal
Provide a component-local, **read-only simulation** command for replaying synthetic perception frames through the real CustomDrive `MissionController`, with deterministic time, a fake motor/robot, per-frame steering alongside source labels, detection confidence, MAE, controller state transitions, failure events and reproducible source/controller hashes. Never initialize physical motors/camera/arm.

## Prior gap / cause
Existing demo and Mission 1 tests cover individual behaviors but do not produce portable, deterministic mission replay reports for comparing controller updates and detecting state regressions before Pi hardware rollout. Treating a perception detector's confidence as steering confidence would also be misleading; the report separates them explicitly.

## Source and anti-rollback review
- Built on **CustomDrive 0_5_20 draft PR #34 (U28)**, stacked on #24 (U23), #21 (U22) and #11 (U24).
- Inspected patch notes **0_5_20, 0_5_19, 0_5_18, 0_5_17** and the actual `MissionController`, `FakeRobot`, `MissionConfig`, `FramePerception`, and command/state interfaces.
- Confirmed exact Git blob hashes for the current six controller dependencies match the locally tested `PiDrive-main.zip` copies. This regression suite therefore exercises the actual live controller/fake-robot sources.
- Preserves existing Mission 1 safety latch, arm roles, pickup/drop-off guide semantics, UI, web/headless/GUI launchers, model detection, and saved configurations.

## Files added (no existing runtime files replaced)
- `CustomDrive/scripts/replay_mission.py`
- `CustomDrive/scripts/fixtures/mission_replay.json`
- `CustomDrive/tests/test_replay_mission.py`
- `CustomDrive/PATCH_NOTES/PATCH_NOTES_CustomDrive_U29.md`

## Commands
From `CustomDrive/`:

```bash
python3 scripts/replay_mission.py --fixture scripts/fixtures/mission_replay.json
python3 scripts/replay_mission.py --fixture scripts/fixtures/mission_replay.json --max-steering-mae 0.12 --report /tmp/customdrive-replay.json
python3 -m unittest discover -s tests -p 'test_replay_mission.py' -v
```

- Fixture JSON version 1 lists **synthetic perception frames** with deterministic timestamps, optional detection boxes/labels/confidence, optional source steering labels and expected mission states. The production mission controller computes steering, but only `FakeRobot` receives its commands.
- Reports per-frame virtual time, state, predicted steering/throttle, optional label/error, maximum **detection** confidence, `steering_confidence=null` (not estimated), fake motor commands, aggregate steering MAE, state mismatches, terminal failures, source fixture SHA-256 and exact controller source SHA-256.
- Optional `--max-steering-mae` allows CI regression thresholds; failure events also produce nonzero exit status. Report creation uses exclusive create and refuses overwriting source fixture. No config, model weights or source fixture are modified.
- This is controller/perception replay, **not YOLO/TFLite model inference**: model path and model SHA-256 are intentionally null. A dataset for a real object detector requires a separate supervised inference test; this runner proves state/controller changes with fixed detections.

## Verification actually performed
- **6/6** `test_replay_mission.py` tests passed on Python 3.13 against the exact live-compatible CustomDrive mission controller source, covering determinism, correct mean absolute steering error, input hashing, fake motor isolation, expected-state mismatch, explicit terminal mission failure, malformed perception/time refusal, exclusive report output and CI thresholds.
- New script/test Python compilation passed. Fixture produces six synthetic steps, steering MAE **0.11552083**, terminal state `align_to_target`, no failure events.
- No Raspberry Pi camera, GPIO, servo arm, TFLite/YOLO, Flask web UI, live hardware mission, or full stacked CustomDrive test suite was run.

## Limits and next steps
- Replayed boxes are synthetic detections; detector confidence is not motor-command confidence and controller outputs alone do not prove driving safety.
- Controller failure detection uses static synthetic inputs. Hardware ownership leases, actual stop timing, camera freshness, servo pose confirmation and other U22/U28 live behaviors still need Pi-side testing.
- No runtime version is promoted and no launcher/UI/config source was edited; this is an optional tooling-only U29 draft built on 0_5_20.
