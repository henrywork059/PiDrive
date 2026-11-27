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


## Owner-directed development merge — 2026-11-28

Owner explicitly directed merging all remaining PRs, including the unqualified development candidates. Integrate exact release #99 66efc009e7db1e607265f273b8b0c1cdfbe98a8b and theme #103 680c26ac10e5ec74aae8c1178148a77eabc59047 on previously qualified main 9285733eeb3c392a86ee0615d1e6bcf71eaf08ab. Preserve both histories, all prior notes, Update B, current main docs, config and safety. Shared regression.yml retains release performance gates AND theme tests; package helper retains authorized version transitions AND exact two-SVG allowlist; package tests retain both sets. No release/physical/visual acceptance, stable baseline promotion, tag or deployment. Main development candidate version is 1.0.0. Trainer online manifest latest/allowed 1.0.0 comes from #99, with minimum and blocked versions unchanged.

Known #103 hardware-free failure 46041965199: PiSD job 140651775605 check_vd1a_web.py line 109 fails buttonScale preservation; PiServer job 140651775652 test_accessibility_r35.cjs line 27 fails existing focus contract. Trainer and compatibility jobs passed; browser 46041965195, native Qt 46041965285, trainer visual 46041965189 passed. #99 replacement CI 46042143183, 46042143228, 46042143157 not yet complete; emulator 46042143245, native Qt 46042143147 and visual 46042143387 passed. Do not weaken failing tests or infer complete VD04–VD07 qualification. Exact integrated main CI and follow-up repair are mandatory before release qualification. Owner merge authorization supersedes the earlier no-merge condition only for development integration.
