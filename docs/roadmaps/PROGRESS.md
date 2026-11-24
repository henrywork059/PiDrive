# Active roadmap progress — 2026-11-24

Scope: PiSD, PiServer and piTrainer. Count original proposal IDs once (not PRs or component-specific patches). The 75 original IDs are preserved. Retire 14 exclusive CustomTrainer/CustomDrive IDs: U18, U22, U24, U25; R33, R41, R42, R44; UX66–UX71. Additionally retire PiBooter-only U16, U19, R34, UX72, UX73. Retired total: 19; active total: 56. R48 remains active for PiSD/PiServer, whose passive preflight implementation and regression checks are present; the sole outstanding PiBooter portion is out of scope.

## Implementation coverage

This is a conservative planning audit based on the four original roadmap documents, merged/pending PR titles, relevant current source, and green integration PR #84 / CI run 45349043534. "Implemented" means a corresponding implementation is present in the candidate and no further active implementation gap was identified in this review; it is not a claim of exhaustive proposal acceptance, physical hardware testing, or merge into main. Partial means specific further work/verification remains. "No dedicated update" means no distinct PR implementing that proposal was identified; overlap from prior work is not counted as completion.

| Track | Active | Implemented | Partial | No dedicated update | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| F1–F10 | 10 | 3 | 3 | 4 | 7 |
| U11–U29 | 13 | 12 | 1 | 0 | 1 |
| R30–R53 | 19 | 11 | 4 | 4 | 8 |
| UX54–UX75 | 14 | 0 | 0 | 14 | 14 |
| Total | 56 | 26 | 8 | 22 | 30 |

Implemented IDs: F1, F5, F6; U11, U12, U13, U14, U15, U17, U20, U23, U26, U27, U28, U29; R30, R31, R32, R37, R38, R39, R40, R43, R46, R47, R48. Evidence: merged PRs #9–42 (active portions), pending PRs #44–79 (active portions), and #81–84. F5 uses the stale-camera timeout contract; F6 uses the passing active regression matrix.

| Partial ID | Remaining work |
| --- | --- |
| F2 | PiSD server-side manual command lease; PiServer watchdog is present. |
| F3 | PiSD access policy; PiServer access control is present. |
| F4 | Both validation scripts imported missing helpers; follow-up patch targets actual production methods. Full standalone command success outstanding. |
| U21 | PiServer autonomous stale-frame enforcement/rearm audit; PiSD guard is present. |
| R35 | Complete active desktop accessibility/input audit. |
| R36 | Complete actual responsive screenshot/interaction acceptance at required widths. |
| R45 | Finish PiSD token/drift audit. |
| R49 | Complete PiSD sanitized bounded operator event view. |

No dedicated update: F7–F10 (config recovery, refactoring, dependencies/packaging, full recording/model workflow); R50–R53 (visual/interaction tests, full provenance, modular extraction, release/anti-rollback checks); UX54–UX65, UX74–UX75. Prior CI, contract and provenance work overlaps several of these but is not treated as full completion.

## Consolidated execution schedule

The 30 remaining original proposal IDs are now organized into **9 development batches** (Batch 1 in progress; 8 not started). See [DEVELOPMENT_SCHEDULE.md](DEVELOPMENT_SCHEDULE.md) for the complete mapping, dependencies and acceptance gates. All 30 IDs appear exactly once. The 26/56 implementation count reflects scope retirement, not new implementation. Track both original IDs and batch status after each update. No retired-component work or hardware acceptance claimed.

## Release candidate
Previous PR #84: PiSD 0.11.22, PiServer 0.4.28, piTrainer 0.11.10 (then also PiBooter 0.1.8). CI run 45349043534: all five jobs passed. Main remains unchanged. The F4 follow-up is separately stacked on the green candidate; its CI run 45353829480 passed the four new math cases and other active jobs but failed the standalone PiSD validation step (standard validation 59 passed / 4 failed). F4 is still partial. The three-component replacement preserves active runtime fixes and the separate F4 follow-up; retirement does not fix these failures.

## Current three-component candidates

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) passed all four jobs in [CI run 45354927996](https://github.com/henrywork059/PiDrive/actions/runs/45354927996). [PR #87](https://github.com/henrywork059/PiDrive/pull/87) retains the F4 validation follow-up; [CI run 45354955594](https://github.com/henrywork059/PiDrive/actions/runs/45354955594) passed three of four jobs but failed the PiSD standalone validation step. Neither candidate has been merged or physically accepted. The progress counts describe the candidate implementation, not a released main-branch runtime. Publishing this plan does not merge runtime code or increment any component version.
