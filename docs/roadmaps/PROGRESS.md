# Active roadmap progress — 2026-11-24

Scope: PiSD, PiServer and piTrainer. Count original proposal IDs once (not PRs or component-specific patches). The 75 original IDs are preserved. Retire 14 exclusive CustomTrainer/CustomDrive IDs: U18, U22, U24, U25; R33, R41, R42, R44; UX66–UX71. Additionally retire PiBooter-only U16, U19, R34, UX72, UX73. Retired total: 19; active total: 56. R48 remains active for PiSD/PiServer, whose passive preflight implementation and regression checks are present; the sole outstanding PiBooter portion is out of scope.

## Implementation coverage

This is a conservative planning audit based on the four original roadmap documents, merged/pending PR titles, relevant current source, and green active integration PR #86 plus Batch 1/2 follow-up PR #87 / CI run 45359079601. "Implemented" means a corresponding implementation is present in the candidate and no further active implementation gap was identified in this review; it is not a claim of exhaustive proposal acceptance, physical hardware testing, or merge into main. Partial means specific further work/verification remains. "No dedicated update" means no distinct PR implementing that proposal was identified; overlap from prior work is not counted as completion.

| Track | Active | Implemented | Partial | No dedicated update | Remaining |
| --- | ---: | ---: | ---: | ---: | ---: |
| F1–F10 | 10 | 8 | 0 | 2 | 2 |
| U11–U29 | 13 | 13 | 0 | 0 | 0 |
| R30–R53 | 19 | 12 | 5 | 2 | 7 |
| UX54–UX75 | 14 | 1 | 1 | 12 | 13 |
| Total | 56 | 34 | 6 | 16 | 22 |

Implemented IDs: F1, F2, F3, F4, F5, F6, F7, F9; U11, U12, U13, U14, U15, U17, U20, U21, U23, U26, U27, U28, U29; R30, R31, R32, R37, R38, R39, R40, R43, R46, R47, R48, R53; UX74. Evidence: merged PRs #9–42 (active portions), pending PRs #44–79 (active portions), and #81–87. F2, F3, F4, U21, F7 and UX74 have tested commits in #87. F5 uses the stale-camera timeout contract; F6 uses the passing active regression matrix.

| Partial ID | Remaining work |
| --- | --- |
| R35 | Complete active desktop accessibility/input audit. |
| R36 | Complete actual responsive screenshot/interaction acceptance at required widths. |
| R45 | PiSD token guide and drift checks committed; exact-candidate CI pending. |
| R50 | Native Chromium and Qt foundation committed; baseline geometry, interaction and review gate pending. |
| UX75 | Initial shared UI acceptance gate committed; full active user journeys and visual review remain. |
| R49 | Complete PiSD sanitized bounded operator event view. |

No dedicated update: F8, F10 (refactoring, full recording/model workflow); R51–R52 (full provenance, modular extraction); UX54–UX65. Prior CI, contract and provenance work overlaps several of these but is not treated as full completion.

## Consolidated execution schedule

The original 30 outstanding IDs were organized into **9 development batches**. Batches 1–3 are complete at the scoped automated implementation gate, and 6 batches remain. Eight of the original 30 have passed, leaving **22 outstanding** in **6 remaining batches**. See [DEVELOPMENT_SCHEDULE.md](DEVELOPMENT_SCHEDULE.md) for the complete mapping, dependencies and acceptance gates. All 30 scheduled IDs remain listed exactly once for traceability. Candidate implementation coverage is 34/56 (60.7%). Track both original IDs and batch status after each update. No retired-component work or hardware acceptance claimed.

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

Current candidate: PiSD **0.11.29**, PiServer **0.4.32**, piTrainer **0.11.13** at 793b3e2. Batches 1–3 have passed their scoped automated gates. Batch 4 in progress. Last verified fully green candidate: 53b06b7 (0.11.28/0.4.32/0.11.12). UX74 confirms exact targets, guards repeated UI submissions, retains soft-hide recovery and does not gate STOP. Actual browser/Windows acceptance is still outstanding; UI guards are not distributed idempotency. Before runtime merge, reconcile this canonical main-branch roadmap with the candidate's older documentation snapshots. LAN startup now requires PISD_ACCESS_TOKEN, including existing systemd services; see PiSD README before deployment. The in-process watchdog does not guarantee physical motor stop if drivers or the OS block; the PiServer frame guard does not independently stop during indefinitely stalled inference. No physical Raspberry Pi acceptance, native Windows UI acceptance, deployment or runtime merge is claimed. The progress counts describe candidate implementation, not a released main-branch runtime. No inactive component work.

## Batch 3 implementation evidence — gate passed

| ID | Candidate commit | Verification |
| --- | --- | --- |
| R53 | [d202082](https://github.com/henrywork059/PiDrive/commit/d2020825a6521269c008a6c53720e2adfffa5ea2) | [CI 45379856839](https://github.com/henrywork059/PiDrive/actions/runs/45379856839): all four jobs passed, including patch manifest validation and deliberate invalid archives. |
| F9 | [c532e1d](https://github.com/henrywork059/PiDrive/commit/c532e1d3730583dafe4207d49cfd0e528d51bfa2) | [CI 45380096413](https://github.com/henrywork059/PiDrive/actions/runs/45380096413): PiSD/PiServer clean dependency and regression steps passed; manifest job passed; piTrainer clean-install step cancelled by successor. |
| F9/R53 | [aaca313](https://github.com/henrywork059/PiDrive/commit/aaca3132184495c92f13ae0f20e3d3ec4f7bb99f) | [CI 45380376438](https://github.com/henrywork059/PiDrive/actions/runs/45380376438): 10 package tests and all three real forward worktree archives passed (7/6/6 files); PiSD clean audit passed, PiServer clean audit found undeclared Pillow in camera diagnostic fallback, trainer smoke cancelled by successor. |

| F9 correction | [53b06b7](https://github.com/henrywork059/PiDrive/commit/53b06b7c5d2c063e21386daf1476856bbd5e01d3) | Declare Pillow in PiServer core requirements; preserve import inventory enforcement; update component patch notes with verified evidence. [CI 45380631288](https://github.com/henrywork059/PiDrive/actions/runs/45380631288) all four jobs passed, including all clean installs and real candidate dry-runs. |

F9 and R53 completed at the scoped automated gate. Current code diff from 8c979f3 changes component dependency declarations, installation docs, patch notes and version constants only; remaining changes are shared release tooling/tests/CI/docs. No previous runtime or UI behavior removed; no persisted config/user files or inactive trees edited. Git-backed package checks require a trusted exact baseline/target, full history, and clean source preimages. They do not authenticate commits, detect all semantic rollbacks, guarantee absence of embedded secrets or apply a patch. Native Windows, OS-specific Pi dependencies, actual training, browser and physical acceptance remain separate. No production archive released. Next: Batch 4.

## Batch 4 — initial implementation

[793b3e2](https://github.com/henrywork059/PiDrive/commit/793b3e25b3100b05da0454ea3da56cf892f77aad): PiSD 0.11.29 token guide, named focus tokens with unchanged defaults and drift check; piTrainer 0.11.13 accessible session-root and checkbox names, keyboard list resize/reset with existing persistence and bounds, and native Qt tests; shared Chromium fixture on actual templates with blocked mutations, four viewport widths, keyboard/touch interaction, failure feedback and screenshot artifacts. Exact candidate CI pending. No owner visual acceptance, physical hardware, Windows, or complete active user-journey acceptance claimed. R35, R36, R45, R50 and UX75 remain outstanding; no Batch 4 completion increment.
