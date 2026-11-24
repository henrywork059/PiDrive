# Stabilization and release acceptance gate

Date: 2026-11-24. Merged starting point: `c615c73032d62daa23ec0fe302d1cfe6049428c3`.

## Purpose and scope

Active development: PiSD, PiServer, piTrainer and PiBooter only. CustomTrainer and CustomDrive are inactive historical components; do not create, reopen, merge or continue their component-specific updates unless explicitly requested. Preserve existing source and history. Shared active-runtime safety and model-family rejection checks remain in scope.

The existing component tests had no repository-level Actions workflow. This change adds an explicitly selected hardware-free regression matrix and a cross-component model-manifest contract test. It changes no application code, launchers, settings, models, or release versions. No existing tests are removed. Newer draft component updates must remain on their own chains; do not replace them with the merged snapshot.

At initial inspection 38 component draft PRs (#43–#80) were open. On 2026-11-24, 13 CustomTrainer/CustomDrive drafts were closed unmerged at the user's direction. The remaining active chains are preserved; PiSD PR #82 adds the STOP latch fix. Do not allocate new patch numbers from merged versions alone or mark draft changes as deployed. Check dependencies and the current branch head before each component update.

| Component | Merged version | Latest open draft at inspection |
| --- | --- | --- |
| PiSD | 0.11.15 | #82, 0.11.22 (STOP latch hotfix) |
| PiServer | 0.4.20 | #78, 0.4.28 |
| piTrainer | 0.11.3 | #69, 0.11.9 |
| PiBooter | 0.1.3 | #79, 0.1.8 |

## Automated checks

The workflow uses fresh GitHub-hosted Linux runners, Python 3.11 and Node 22, with test-only dependencies. It does not install GPIO/Picamera2 or launch a hardware runtime. Each selected Python file runs in its own process and a missing, failing, empty or skipped Python test file fails its job. JavaScript files are invoked with Node. Each component is independently reported; a failure does not cancel the other matrix jobs. Cross-component tests use the actual three active manifest helpers and dummy artifacts to check family, input size, checksum, malformed and legacy behavior. They do not run TensorFlow Lite inference or claim YOLO support in PiSD or PiServer's steering application.

Local contract check from repo root:
```sh
python -m unittest discover -s tests -p test_cross_component_manifests.py -v
```

See the workflow matrix for the exact test-only package constraints and file selection; run the same Python and Node commands from the named component folder. Do not treat this curated matrix as coverage of every test or GUI path. Add new hardware-free tests to the matrix after reviewing their dependencies and isolation. An absent or failed CI result is not a pass.

## Physical acceptance (P0)

Perform only under direct operator supervision, in a controlled area with clear surroundings and a reachable physical power disconnect. Begin with motors disconnected or wheels raised, no autonomous drive running and no autonomous restart; do not test on an occupied road. Keep the physical stop available throughout. Verify actual motion ceases independently of UI indicators. If any check fails, stop and withhold promotion; never bypass a latch to finish testing.

Record commit SHA, component version, hardware/OS, camera and motor adapter, timestamp, operator, evidence and PASS/FAIL/NOT RUN for each check.

| Check | Expected result |
| --- | --- |
| Manual STOP and command loss | Output stops; no unintended restart. |
| AI stale/disconnected camera | Fault stops output and remains latched; fresh frames alone do not restart motion. |
| Explicit rearm | Reject while fault or stop cannot be verified; successful rearm alone does not move the robot. |
| Competing runtime hardware claim | Second runtime fails closed without stealing camera/motor ownership. |
| Settings apply and restart | Effective values and persisted configuration match; failures show failure, not success. |
| Incompatible/corrupt model | Reject before activation; previous valid model remains available. |

After P0, validate actual trainer export → runtime preflight with known safe models, then supervised Manual Drive and AI Mode operation, Wi-Fi onboarding, and desktop/mobile UI behavior. Do not use synthetic model bytes for physical runtime tests.

## Verification and release policy

The initial CI run (https://github.com/henrywork059/PiDrive/actions/runs/45341112481) passed piTrainer, PiBooter and manifest compatibility but exposed PiSD STOP latch and PiServer outdated camera mock failures. The revised active-only workflow must be rerun; no physical hardware, Windows GUI, real model training or live inference was tested. Keep stable baselines distinct from merged commits and draft changes. Before merge, inspect CI results and resolve failures on the appropriate component branch. Do not mark a release hardware-validated without separate recorded physical acceptance.
