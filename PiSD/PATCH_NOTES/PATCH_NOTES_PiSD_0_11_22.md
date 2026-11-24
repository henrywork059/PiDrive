# PiSD 0.11.22 — STOP must retain the camera-fault latch

## Request and root cause
P0 stabilization regression gate PR #81 exposed an actual merged-main failure: `scripts/test_safety_rearm.py::U28SafetyRearmTests::test_contract_and_latch_survives_stop` failed because `AIDriveService.stop()` unconditionally reset `_camera_frame_fault_latched`. The CI run is https://github.com/henrywork059/PiDrive/actions/runs/45341112481. This behavior contradicts the existing U28 explicit-rearm contract.

## Baseline and anti-rollback
Direct parent is latest PiSD draft PR #76 (R48, 0.11.21), commit 6644b85e9e22d1e32369a310467e457d92b4112a. The service file has the identical Git blob SHA on merged main and R48 (d4668f7d36478f97505673750d6ad9a3943fcccc). Reviewed R48, R47, R46 and R43 notes and the real PiSD.py launcher. Preserve passive preflight, tracing/redaction, UI copy, hidden-stream controls, R32 command provenance, settings feedback, storage and model preflight. The patch changes no UI, runtime config, motor mixing, or model data.

## Changed files
- `PiSD/pisd/services/ai_drive_service.py`: remove only STOP's unconditional latch reset. Existing explicit rearm checks, stop behavior, transient reset and zero-output logic remain.
- `PiSD/scripts/test_safety_rearm.py`: retain existing failing regression and add repeated-stop, failed-stop and explicit-rearm checks.
- `PiSD/scripts/test_ai_frame_timeout.py`: update fake motor signature to accept R32's diagnostic control_source keyword, without changing its simulated command behavior.
- `PiSD/pisd/__init__.py`: advance latest pending 0.11.21 to 0.11.22.
- This patch note.

## Verification actually performed
The merged baseline failure was executed on GitHub Actions and the exact faulty assignment was confirmed on main and the latest pending branch. Source anchors checked before targeted edit. The new patch tests require execution against this exact branch; CI on merged main is not evidence of the fixed branch passing. No hardware, inference or physical motor verification was performed. Do not deploy until regression and physical acceptance pass.

## Limits
This is an in-process latch fix, not a physical emergency-stop relay or a guarantee of latch persistence across a full application restart. Merge after its parent chain and the regression gate; retain operator rearm checks.
