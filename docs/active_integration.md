# Active-component integration candidate

2026-11-24. This replacement integration combines the three active component draft tips and the regression gate. It preserves the exact latest active component trees from the previous integration, but deliberately excludes all unmerged PiBooter ancestry and changes. This is a draft candidate, not a deployed release.

| Component | Source PR | Exact source commit |
| --- | --- | --- |
| PiSD 0.11.22 | #82 | `c402a449fa1be7ebef700ae1398ad33a896914dc` |
| PiServer 0.4.28 + test fix | #83 | `c22a3768e845c53880e9df772c21b8822d4922cf` |
| piTrainer 0.11.9 | #69 | `180288b318f4b4ba544d65051e0dc65098f3478e` |
| Active regression gate | #81 | `a767cdbebf446fe959ec89afac77794f0555b674` |

The full component trees are taken from the latest pending branches, not old uploaded ZIPs or earlier merged versions. GitHub comparisons confirmed each component stack changed only its own directory relative to main. Inactive PiBooter, CustomDrive and CustomTrainer trees are byte-identical to merged main. Prior four-component PR #84 and F4 follow-up #85 are superseded, not merged. No new version allocated for integration.

The workflow adds pending-branch regression tests to the existing matrix, including offscreen Qt tests, and continues across individual test files so one failure cannot conceal later failures. It does not run real GPIO, cameras, motors, model training. A failure is a release blocker, not a reason to skip a test. Physical checks in stabilization_acceptance.md still apply. Do not merge before review and authorization.

## Integration follow-up (2026-11-24)

The piTrainer source stack was advanced to 0.11.10 in commit `3d450015564af5f0b108c21e5b016a4c1c59c374` to fix selection identity across Qt sorting. CI run [45342699744](https://github.com/henrywork059/PiDrive/actions/runs/45342699744) passed 19 selection-scope cases and the other active component jobs; only an obsolete exact-version R46 assertion failed. The assertion now requires a forward patch in the existing series and matching version markers. This is still an unmerged candidate; no physical acceptance has been performed.

## Scope reduction

PiBooter was retired by explicit user instruction. Retain merged PiBooter 0.1.3; do not merge its pending 0.1.4–0.1.8 stack. The replacement baseline uses the exact PiSD, PiServer and piTrainer trees from e90f78705222880e75f6da4c8f2a9d1ef41389f1; the separate F4 follow-up retains the exact active trees from 4ee2f6d627e9a8cc7e72a0905832c5641176dad6. The previous all-green run remains historical evidence, not a substitute for the reduced-scope CI. No runtime version increment.
