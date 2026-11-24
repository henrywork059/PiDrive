# Active roadmap progress — 2026-11-24

Scope: PiSD, PiServer and piTrainer. Count original proposal IDs once (not PRs or component-specific patches). The 75 original IDs are preserved. Retire 14 exclusive CustomTrainer/CustomDrive IDs: U18, U22, U24, U25; R33, R41, R42, R44; UX66–UX71. Additionally retire PiBooter-only U16, U19, R34, UX72, UX73. Retired total: 19; active total: 56. R48 remains active for PiSD/PiServer, whose passive preflight implementation and regression checks are present; the sole outstanding PiBooter portion is out of scope.

## Implementation coverage

This is a conservative planning audit based on the four original roadmap documents, merged/pending PR titles, relevant current source, and green active integration PR #86 plus Batch 1/2 follow-up PR #87 / CI run 45359079601. "Implemented" means a corresponding implementation is present in the candidate and no further active implementation gap was identified in this review; it is not a claim of exhaustive proposal acceptance, physical hardware testing, or merge into main. Partial means specific further work/verification remains. "No dedicated update" means no distinct PR implementing that proposal was identified; overlap from prior work is not counted as completion.

| Track | Active | Implemented | Partial | No dedicated update | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| F1–F10 | 10 | 7 | 0 | 3 | 3 |
| U11–U29 | 13 | 13 | 0 | 0 | 0 |
| R30–R53 | 19 | 11 | 4 | 4 | 8 |
| UX54–UX75 | 14 | 1 | 0 | 13 | 13 |
| Total | 56 | 32 | 4 | 20 | 24 |

Implemented IDs: F1, F2, F3, F4, F5, F6, F7; U11, U12, U13, U14, U15, U17, U20, U21, U23, U26, U27, U28, U29; R30, R31, R32, R37, R38, R39, R40, R43, R46, R47, R48; UX74. Evidence: merged PRs #9–42 (active portions), pending PRs #44–79 (active portions), and #81–87. F2, F3, F4, U21, F7 and UX74 have tested commits in #87. F5 uses the stale-camera timeout contract; F6 uses the passing active regression matrix.

| Partial ID | Remaining work |
| --- | --- |
| R35 | Complete active desktop accessibility/input audit. |
| R36 | Complete actual responsive screenshot/interaction acceptance at required widths. |
| R45 | Finish PiSD token/drift audit. |
| R49 | Complete PiSD sanitized bounded operator event view. |

No dedicated update: F8–F10 (refactoring, dependencies/packaging, full recording/model workflow); R50–R53 (visual/interaction tests, full provenance, modular extraction, release/anti-rollback checks); UX54–UX65, UX75. Prior CI, contract and provenance work overlaps several of these but is not treated as full completion.

## Consolidated execution schedule

The original 30 outstanding IDs were organized into **9 development batches**. Batches 1 and 2 are complete at the scoped automated implementation gate, and 7 batches remain. Six of the original 30 have passed, leaving **24 outstanding** in **7 remaining batches**. See [DEVELOPMENT_SCHEDULE.md](DEVELOPMENT_SCHEDULE.md) for the complete mapping, dependencies and acceptance gates. All 30 scheduled IDs remain listed exactly once for traceability. Candidate implementation coverage is 32/56 (57.1%). Track both original IDs and batch status after each update. No retired-component work or hardware acceptance claimed.

## Release candidates and Batch 1–2 evidence

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) remains the green three-component integration baseline: PiSD 0.11.22, PiServer 0.4.28, piTrainer 0.11.10; [CI 45354927996](https://github.com/henrywork059/PiDrive/actions/runs/45354927996), all four jobs passed.

[PR #87](https://github.com/henrywork059/PiDrive/pull/87) advances the candidate through separately reviewable changes:

| ID | Component/version | Commit | Verified automated gate |
| --- | --- | --- | --- |
| F4 | PiSD 0.11.23 | d4fc167 | [45356440576](https://github.com/henrywork059/PiDrive/actions/runs/45356440576): all four jobs passed; standard validation 63/63; STOP outcome and rearm regressions |
| U21 | PiServer 0.4.29 | ea60df3 | [45356590242](https://github.com/henrywork059/PiDrive/actions/runs/45356590242): all four jobs passed; fresh raw frame, stale-frame and explicit rearm cases |
| F2 | PiSD 0.11.24 | d7b1ef2 | [45356933493](https://github.com/henrywork059/PiDrive/actions/runs/45356933493): all four jobs passed; manual lease expiry, renew, STOP and owner changes |
| F3 | PiSD 0.11.25 | 413b938 | [45357578563](https://github.com/henrywork059/PiDrive/actions/runs/45357578563): all four jobs passed; LAN access, origin checks and authorized STOP |
| F7 | PiSD 0.11.26 | f11abb02 | [45358045630](https://github.com/henrywork059/PiDrive/actions/runs/45358045630): all four jobs passed; six new recovery cases; standard validation 63/63 |
| F7 | PiServer 0.4.30 | adf44de | [45358221582](https://github.com/henrywork059/PiDrive/actions/runs/45358221582): all four jobs passed; seven config-store cases and one real API recovery case |
| UX74 | PiSD 0.11.27 / PiServer 0.4.31 / piTrainer 0.11.11 | 8c979f3 | [45359079601](https://github.com/henrywork059/PiDrive/actions/runs/45359079601): all four jobs passed; explicit confirmation, non-modal duplicate guard, exact trainer purge scope and stale-plan refusal |

Current candidate: PiSD **0.11.27**, PiServer **0.4.31**, piTrainer **0.11.11**. Batches 1 and 2 have passed their scoped automated gates. Next: Batch 3 (F9/R53 dependency and release packaging safeguards). Last verified green candidate: 8c979f3. UX74 confirms exact targets, guards repeated UI submissions, retains soft-hide recovery and does not gate STOP. Actual browser/Windows acceptance is still outstanding; UI guards are not distributed idempotency. Before runtime merge, reconcile this canonical main-branch roadmap with the candidate's older documentation snapshots. LAN startup now requires PISD_ACCESS_TOKEN, including existing systemd services; see PiSD README before deployment. The in-process watchdog does not guarantee physical motor stop if drivers or the OS block; the PiServer frame guard does not independently stop during indefinitely stalled inference. No physical Raspberry Pi acceptance, native Windows UI acceptance, deployment or runtime merge is claimed. The progress counts describe candidate implementation, not a released main-branch runtime. No inactive component work.
