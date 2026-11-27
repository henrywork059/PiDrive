# PiDrive 1.0.0 release candidate

Owner decision, 2026-11-28: all three active components use 1.0.0, not 0.12.0 or 0.5.0. Subsequent bug-fix versions are 1.0.x; later minor/major families require explicit approval.

| Component | Exact integration parent version | Candidate |
|---|---|---|
| PiSD | 0.11.49 | 1.0.0 |
| PiServer | 0.4.56 | 1.0.0 |
| piTrainer | 0.11.36 | 1.0.0 |

Parent PR #98 at a4b9496b9c5d302b9a574e7e69984d8686b13b4f; integration CI is pending. This separate stacked draft avoids interrupting its current qualification. Keep all runtime, authentication, STOP, emulator, camera, trainer performance and data-integrity fixes. Preserve historic notes and previous accepted rollback baselines. Legacy/inactive components are excluded. Online trainer manifest retains its previous minimum and blocked-version policy; candidate latest is 1.0.0, with no live main change until acceptance.

## Gates
- Complete exact corrected PR #98 CI and integration/merge; close original superseded PRs only after verifying their changes are included.
- Reconcile this draft onto the accepted main with exact candidate ancestry. Execute all six workflows, verify manifests and actual full stable-package contents, checksums and paths; no generated data, local settings or secrets in release bundles.
- Review native/web visual evidence and outstanding target-environment checks, record physical P0 acceptance per docs/stabilization_acceptance.md. Do not claim hardware safety from simulation.
- After successful gates, merge/promote accepted baseline, update stable baseline records, build full component archives, and publish the release/tag if approved. No tag, published stable release or deployment is created by this draft.


## Reconciliation checkpoint

Qualified main 9285733eeb3c392a86ee0615d1e6bcf71eaf08ab: post-integration regression 46041460253 and browser 46041460357 passed. Reconcile the release branch on this exact main, not stale #98. Prior release regression 46034291646 failed old version-family assertions in PiSD test_responsive_r36.cjs/test_ui_copy_r46.cjs, PiServer test_request_trace_ui_r47.cjs/test_responsive_r36.cjs/test_ui_copy_r46.cjs and piTrainer test_ui_copy_r46.py/test_ui_style_contract_r45.py. Direct logs inspected; preserve legacy floors, accept explicit 1.0.x, and verify full trainer version/patch match. No acceptance threshold for runtime safety or feature tests changed. New exact CI pending. Concurrent theme #103 is independently changing and remains to be reconciled; no release/physical acceptance claimed.
