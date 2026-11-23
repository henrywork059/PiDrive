# PiSD U29 — Safe replay and steering regression diagnostics

## Request and goal
Implement roadmap U29's component-local replay command. Replay a synthetic session or existing PiSD recording labels with offline model inference, display per-frame predictions beside source steering labels, mean absolute error, failure events, deterministic virtual time and reproducible source/model hashes. Never energize motors or modify source sessions.

## Cause / prior gap
Existing AI tests validate inference and safety paths but do not offer a replayable end-to-end **read-only dataset regression report**. Deployments lacked a deterministic fixture-level comparison of source labels to predicted steering before hardware testing. A steering regression model does not provide calibrated confidence; do not invent it.

## Source and anti-rollback review
- Built on **PiSD 0.11.13 draft PR #32 (U28)**, itself stacked on PR #30 (U27), #26 (U26), #22 (U23), #20 (U20), and #12 (U21).
- Read patch notes **0.11.13, 0.11.12, 0.11.11, 0.11.10** plus the actual recording label schema and AI model-loading functions.
- Preserves accepted camera/AI/motor behavior, UI, U28 rearm latch, U27 model preflight/rollback, U26 low-disk guardrails, U20 repair, user configuration and recordings; no application runtime code changed.
- Main entry point remains `PiSD/PiSD.py`; tooling is an optional offline command and does not modify it.

## Files added (no existing runtime files replaced)
- `PiSD/scripts/replay_session.py`
- `PiSD/scripts/fixtures/steering_replay.jsonl`
- `PiSD/scripts/test_replay_session.py`
- `PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_U29.md`

## Behavior and exact commands
From `PiSD/`:

```bash
python3 scripts/replay_session.py --fixture scripts/fixtures/steering_replay.jsonl
python3 scripts/replay_session.py --fixture scripts/fixtures/steering_replay.jsonl --max-steering-mae 0.11
python3 scripts/replay_session.py --session recordings/YYYY-MM-DD/SESSION_DIR --model models/your_steering_model.tflite --report /tmp/pisd-replay.json
python3 -m unittest discover -s scripts -p 'test_replay_session.py' -v
```

- The fixture has **three tiny synthetic JPEG frames encoded as base64**, source steering labels and explicitly synthetic predictions/confidence values. Fixture predictions are **not** a real model evaluation.
- Existing recording sessions use `labels.jsonl` (`frame`, `steering`), resolve images only under the session directory, and require `--model` to perform genuine offline steering inference. Optional `.tflite`, `.keras`, or `.h5` inference uses **only** `AIDriveService.load_model` preflight plus JPEG model inference; **no CameraService, MotorService, GPIO, Flask, or driving loop** is constructed.
- In real-model mode the `prediction_confidence` field is `null`: steering/throttle regressors do not emit calibrated confidence. The synthetic-only fixture may contain explicitly supplied mock confidence values.
- JSON output includes virtual frame time, label/predicted steering, absolute error, session steering MAE, failure events, SHA-256 hashes for the input labels/fixture and optional model, and explicit replay-only safety markers. A `--max-steering-mae` threshold exits nonzero for CI regressions; malformed/missing frames also fail nonzero.
- Output is stdout by default. `--report` refuses overwriting any existing file and refuses paths inside the source session. Source frames and labels remain unchanged. Relative paths escaping the session directory are rejected. Row/frame sizes and record counts are bounded.

## Verification actually performed
- **6/6** `test_replay_session.py` tests passed locally on Python 3.13 using the exact added script and fixture: deterministic metrics, synthetic confidence and hash, invalid prediction failure handling, source path escape rejection, exclusive/non-destructive output, no-motor import, and CI threshold behavior.
- Python compilation of new scripts/tests passed.
- Example fixture reports steering MAE **0.1** across three synthetic samples, with zero failure events.
- Real TFLite/Keras model inference, large real recordings, hardware Pi camera/motor, and full stacked PiSD/Flask suite were **not run**. These require separate verification before stable promotion.

## Limits
- Replay compares **stored labels with model outputs**; it does not determine safe driving quality or closed-loop performance. No physical movement or calibrated steering confidence is asserted.
- Model execution may need numpy, PIL and a compatible TensorFlow Lite/Keras runtime. A selected model must pass the existing U27 preflight; a missing/unavailable runtime yields a clear failure.
- U29 does not modify runtime versions, launchers, saved config, AI page layout or existing sessions. It remains a draft tooling-only patch atop 0.11.13.
