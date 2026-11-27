# Testing and CI playbook

Reference for selecting evidence, not a replacement for the live workflow matrix. Main source inspected at 8f593778eb461f8515f6c12c5fce936dc64cb301. Run only hardware-free tests on an isolated development system, with temporary recordings/config/QSettings. Never run automated mutation checks against a physical car.

## Test tiers

| Tier | Evidence | What it does not prove |
| --- | --- | --- |
| 0 | Source review, syntax/import checks | Runtime correctness |
| 1 | Deterministic unit/contract tests | Full integrated workflow |
| 2 | Actual Flask/Chromium and native Qt test fixtures | Physical safety or visual owner approval |
| 3 | Real model conversion, matched performance workloads, artifact inspection | Physical device/energy claims |
| 4 | Supervised physical P0 and owner acceptance | Unrelated future revisions |

## Select tests by changed surface

Paths below are present in the inspected main. Run Python tests in their component directory using that revision's workflow runner/dependencies; some files are pytest suites, others standalone scripts. Check the exact invocation rather than blindly running all files.

| Change | Relevant tests |
| --- | --- |
| PiSD motor/STOP/lease/access | PiSD/scripts/test_motor_service.py, test_safety_rearm.py, test_stop_outcome_f4.py, test_manual_lease_f2.py, test_access_control_f3.py |
| PiSD camera/AI/recording | PiSD/scripts/test_camera_service.py, test_ai_frame_timeout.py, test_ai_drive_service.py, test_recording_service.py, test_recording_recovery.py |
| PiSD settings/UI | PiSD/scripts/test_config_recovery_f7.py, test_settings_persistence.py, test_settings_feedback.cjs, test_accessibility_r35.cjs |
| PiServer ownership/control/config | PiServer/tests/test_hardware_ownership.py, test_control_service.py, test_safety_rearm_contract.py, test_access_api.py, test_config_recovery_f7.py |
| PiServer preview/recording/UI | PiServer/tests/test_camera_lowres_p2.py, test_preview_yuv_p2.py, test_preview_resource_profile_p2.py, test_preview_freshness.cjs, test_recording_feedback_ux75.cjs |
| Trainer data and selection | piTrainer/tests/test_record_streaming_p2.py, test_filter_positions_p2.py, test_dataset_integrity.py, test_selection_scope.py, test_metadata_atomicity.py |
| Trainer UI and persistence | piTrainer/tests/test_splitter_restore_r50.py, test_splitter_minimums_r50.py, test_validation_to_data_r50.py, test_session_keyboard_r35.py |
| Trainer export and model | piTrainer/tests/test_recording_to_export_f10.py, test_export_manifest.py, test_real_tflite_export_f10.py |
| Cross-component packages/manifests | tests/test_patch_package.py, tests/test_cross_component_manifests.py |
| Emulator | PiSD_Emulator/scripts/test_emulator.py, test_frame_browser.py |

Names after a directory-prefixed entry in each row refer to the same directory. New tests on pending branches must be discovered from that branch, not this table.

## Safe local entry checks

Use Python 3.11 when matching Linux CI, install the appropriate requirements in a disposable environment per [dependency groups](../dependency_groups.md), and use the repository root unless otherwise noted.

```sh
python -m compileall -q PiSD/pisd PiSD_Emulator
python PiSD/PiSD.py --status-only
python PiSD_Emulator/scripts/test_emulator.py
python -m unittest discover -s tests -p test_cross_component_manifests.py -v
python -m unittest discover -s tests -p test_patch_package.py -v
```

These commands are documented/verified against existing entry points; not newly executed for this guide. PiSD status-only defaults to simulation; do not add --hardware. PiServer launcher constructs an app at import; do not launch/import it casually on a hardware-capable host. Consult fixture precautions in [UI gate](../ui_regression_gate.md).

## Exact CI qualification

Main workflows at inspection: [regression.yml](../../.github/workflows/regression.yml) (four jobs), [windows-ui-regression.yml](../../.github/workflows/windows-ui-regression.yml), [performance-strict.yml](../../.github/workflows/performance-strict.yml), [performance-workloads.yml](../../.github/workflows/performance-workloads.yml), [pisd-emulator-frame.yml](../../.github/workflows/pisd-emulator-frame.yml). UI2 trainer visual workflow is present on the pending integration branch; inspect latest target before requiring it. Check triggers/path filters and actual executed jobs, not just workflow existence.

- Match run HEAD, attempt, workflow and job conclusion to exact candidate source. Cancelled, skipped, pending, missing and failed are not PASS. Read first meaningful failure and all matrix outcomes; a later artifact error may be secondary.
- Run new tests with declared dependencies, register them in mandatory applicable CI; preserve no-empty/no-skipped test checks and existing regression assertions.
- Inspect actual screenshot archives, manifest hashes, requested/realized dimensions, font glyphs and geometry; green capture alone is not visual acceptance. Preserve 105 approved web PNGs; use exact pinned baseline described in [baseline review](../ui_baseline_review.md).
- Record exact benchmark baseline and candidate, paired repetitions, workload counts, CPU/RSS, freshness, hashes/parity, trade-offs and misses. Use existing workflow commands rather than substituting isolated microbenchmarks. Immutable original benchmark baseline 14c57c990ff0f9bae2003e4e8aa552d17a4227c7.
- Package dry runs use exact Git baseline and candidate; see [packaging](../patch_package.md). Inherited qualification is valid only under the implemented strict ancestor/tree-identity guard.
- Physical validation remains a separate supervised gate in [stabilization acceptance](../stabilization_acceptance.md). Never bypass it or equate simulation with physical evidence.
