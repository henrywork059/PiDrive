# Stabilization and release acceptance gate

Date: 2026-11-24. Merged starting point: `c615c73032d62daa23ec0fe302d1cfe6049428c3`.

## Purpose and scope

Active development: PiSD, PiServer and piTrainer only. PiBooter, CustomTrainer and CustomDrive are inactive historical components; do not create, reopen, merge or continue their component-specific updates unless explicitly requested. Preserve existing source and history. Shared active-runtime safety and model-family rejection checks remain in scope.

The existing component tests had no repository-level Actions workflow. This change adds an explicitly selected hardware-free regression matrix and a cross-component model-manifest contract test. It changes no application code, launchers, settings, models, or release versions. No existing test source is removed; inactive components are excluded from the active CI matrix. Newer draft component updates must remain on their own chains; do not replace them with the merged snapshot.

At initial inspection 38 component draft PRs (#43–#80) were open. On 2026-11-24, 13 CustomTrainer/CustomDrive drafts were closed unmerged at the user's direction. Five PiBooter drafts (#44, #48, #52, #71, #79) are also retired at the user's direction. The three remaining active chains are preserved; PiSD PR #82 adds the STOP latch fix. Do not allocate new patch numbers from merged versions alone or mark draft changes as deployed. Check dependencies and the current branch head before each component update.

| Component | Merged version | Latest open draft at inspection |
| --- | --- | --- |
| PiSD | 0.11.15 | #82, 0.11.22 (STOP latch hotfix) |
| PiServer | 0.4.20 | #78, 0.4.28 |
| piTrainer | 0.11.3 | integrated 0.11.10 |

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

After P0, validate actual trainer export → runtime preflight with known safe models, then supervised Manual Drive and AI Mode operation, and desktop/mobile UI behavior. Do not use synthetic model bytes for physical runtime tests.

## Verification and release policy

The initial CI run (https://github.com/henrywork059/PiDrive/actions/runs/45341112481) passed piTrainer, PiBooter and manifest compatibility but exposed PiSD STOP latch and PiServer outdated camera mock failures. The former four-component integration passed all five jobs in run 45349043534. The replacement three-component workflow must be rerun; no physical hardware, Windows GUI, real model training or live inference was tested. Keep stable baselines distinct from merged commits and draft changes. Before merge, inspect CI results and resolve failures on the appropriate component branch. Do not mark a release hardware-validated without separate recorded physical acceptance.


## Main integration reconciliation — 2026-11-27

The owner explicitly requested merging all open PiDrive PRs into main. All 24 open PR heads (#45, #46, #49, #50, #53, #54, #55, #56, #59, #61, #63, #64, #66, #67, #69, #72, #73, #75, #76, #78, #82, #83, #86, #87) were individually verified as ancestors of, or equal to, the exact green completed candidate 6aaee7050485a6b1c3f841cd5837db8be4820768. Linux [45960538086](https://github.com/henrywork059/PiDrive/actions/runs/45960538086) 4/4 and Windows [45960538133](https://github.com/henrywork059/PiDrive/actions/runs/45960538133) 1/1 passed. No independent replay of older patches is required.

Previous main 8dfae027ae200757f6adf7669ea8a9b84b8db884 and the completed candidate diverged from c615c73032d62daa23ec0fe302d1cfe6049428c3. Complete recursive Git blob inventories showed no main-only file changes, two identically changed files and five differing documentation paths; 322 candidate-only changed paths. Retain the final candidate's software, version markers, tests, and 56/56 / 9/9 accounting; preserve all previous main commits as the second parent of this reconciliation. Historical main documents remain accessible at the immutable [progress snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/PROGRESS.md), [schedule snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/DEVELOPMENT_SCHEDULE.md), [README](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/README.md), [roadmap index](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/README.md) and [acceptance record](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/stabilization_acceptance.md). Older progress counts are superseded, not deleted from history.

The candidate-first merge-parent order preserves the version-changing first-parent history used by tools/check_forward_packages.py. Integrate by a normal non-forced fast-forward of main to the reconciliation commit, only while both source references remain as verified. No production source, configuration, regression, version marker, retired component, or approved visual baseline changes in this reconciliation. Merge authorization does not imply stable promotion, hardware deployment, native desktop visual or assistive-technology approval. No release tag or new version. Verify final main and its CI separately.

The preceding inspection/version table and initial CI findings above are historical. Current candidate versions are PiSD 0.11.45, PiServer 0.4.53 and piTrainer 0.11.32. All current automated gates passed at the tested source; the exact new reconciliation commit requires its own CI. Physical P0 checks remain unchanged and unperformed. Refer to the [final handover](roadmaps/RELEASE_CANDIDATE_HANDOVER.md).
