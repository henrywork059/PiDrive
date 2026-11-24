# Active roadmap progress — 2026-11-24

Scope: PiSD, PiServer and piTrainer. Count original proposal IDs once (not PRs or component-specific patches). The 75 original IDs are preserved. Retire 14 exclusive CustomTrainer/CustomDrive IDs: U18, U22, U24, U25; R33, R41, R42, R44; UX66–UX71. Additionally retire PiBooter-only U16, U19, R34, UX72, UX73. Retired total: 19; active total: 56. R48 remains active for PiSD/PiServer, whose passive preflight implementation and regression checks are present; the sole outstanding PiBooter portion is out of scope.

## Implementation coverage

This is a conservative planning audit based on the four original roadmap documents, merged/pending PR titles, relevant current source, and green active integration PR #86 plus Batch 1 follow-up PR #87 / CI run 45356933493. "Implemented" means a corresponding implementation is present in the candidate and no further active implementation gap was identified in this review; it is not a claim of exhaustive proposal acceptance, physical hardware testing, or merge into main. Partial means specific further work/verification remains. "No dedicated update" means no distinct PR implementing that proposal was identified; overlap from prior work is not counted as completion.

| Track | Active | Implemented | Partial | No dedicated update | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| F1–F10 | 10 | 5 | 1 | 4 | 5 |
| U11–U29 | 13 | 13 | 0 | 0 | 0 |
| R30–R53 | 19 | 11 | 4 | 4 | 8 |
| UX54–UX75 | 14 | 0 | 0 | 14 | 14 |
| Total | 56 | 29 | 5 | 22 | 27 |

Implemented IDs: F1, F2, F4, F5, F6; U11, U12, U13, U14, U15, U17, U20, U21, U23, U26, U27, U28, U29; R30, R31, R32, R37, R38, R39, R40, R43, R46, R47, R48. Evidence: merged PRs #9–42 (active portions), pending PRs #44–79 (active portions), and #81–87. F2, F4 and U21 have separate tested commits in #87. F5 uses the stale-camera timeout contract; F6 uses the passing active regression matrix.

| Partial ID | Remaining work |
| --- | --- |
| F3 | PiSD access policy; PiServer access control is present. |
| R35 | Complete active desktop accessibility/input audit. |
| R36 | Complete actual responsive screenshot/interaction acceptance at required widths. |
| R45 | Finish PiSD token/drift audit. |
| R49 | Complete PiSD sanitized bounded operator event view. |

No dedicated update: F7–F10 (config recovery, refactoring, dependencies/packaging, full recording/model workflow); R50–R53 (visual/interaction tests, full provenance, modular extraction, release/anti-rollback checks); UX54–UX65, UX74–UX75. Prior CI, contract and provenance work overlaps several of these but is not treated as full completion.

## Consolidated execution schedule

The original 30 outstanding IDs were organized into **9 development batches** (Batch 1 in progress; 8 not started). Three have since passed the scoped automated implementation gate, leaving **27 outstanding**. See [DEVELOPMENT_SCHEDULE.md](DEVELOPMENT_SCHEDULE.md) for the complete mapping, dependencies and acceptance gates. All 30 scheduled IDs remain listed exactly once for traceability. Candidate implementation coverage is 29/56 (51.8%). Track both original IDs and batch status after each update. No retired-component work or hardware acceptance claimed.

## Release candidates and Batch 1 evidence

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) remains the green three-component integration baseline: PiSD 0.11.22, PiServer 0.4.28, piTrainer 0.11.10; [CI 45354927996](https://github.com/henrywork059/PiDrive/actions/runs/45354927996), all four jobs passed.

[PR #87](https://github.com/henrywork059/PiDrive/pull/87) advances the candidate through three separately reviewable changes:

| ID | Component/version | Commit | Verified automated gate |
| --- | --- | --- | --- |
| F4 | PiSD 0.11.23 | d4fc167 | [45356440576](https://github.com/henrywork059/PiDrive/actions/runs/45356440576): all four jobs passed; standard validation 63/63; STOP outcome and rearm regressions |
| U21 | PiServer 0.4.29 | ea60df3 | [45356590242](https://github.com/henrywork059/PiDrive/actions/runs/45356590242): all four jobs passed; fresh raw frame, stale-frame and explicit rearm cases |
| F2 | PiSD 0.11.24 | d7b1ef2 | [45356933493](https://github.com/henrywork059/PiDrive/actions/runs/45356933493): all four jobs passed; manual lease expiry, renew, STOP and owner changes |

Current candidate: PiSD **0.11.24**, PiServer **0.4.29**, piTrainer **0.11.10**. F3 PiSD LAN authorization remains outstanding. Batch 1 is not complete. The in-process watchdog does not guarantee physical motor stop if drivers or the OS block; the PiServer frame guard does not independently stop during indefinitely stalled inference. No physical Raspberry Pi acceptance, native Windows UI acceptance, deployment or runtime merge is claimed. The progress counts describe candidate implementation, not a released main-branch runtime. No inactive component work.
