# Active roadmap progress — 2026-11-27

## Verified software implementation at 5751280f107fb84c87bf0c113902ad49dc323dcd

**50/56 implemented (89.3%), 6 remaining, 6/9 batches complete.** Eight newly accepted IDs: UX55, UX57, UX58, UX59, UX60, UX61, UX63, UX65. Batch 6 and 9 software scope complete; remaining batches 4, 7, 8. Cross-batch completion allowed by owner; physical hardware and owner visual acceptance separate.

Exact verified baseline 5751280f107fb84c87bf0c113902ad49dc323dcd, Linux 45869069010 and Windows 45869069132 passed all five jobs. Actual PiSD artifact 15141562339 SHA-256 5096c95d417f67b914ca74acf139c2e7768a122f7d199dd4d4b703d69481655d and PiServer artifact 15141866729 SHA-256 f30aa64d7b204bf9e1a985b7a241b2040a6c7ca686e3c37a78982e5e6c440140 independently matched; all 78 cases zero errors. Forward packages 11/8/11 files passed. Actual screenshots inspected. Native review-context 7/7 Linux and Windows. AI preview non-overlap and Manual draft reset 5/5; preset preview/cancel all three at all five sizes, full telemetry and action hierarchy checks passed.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 9 | 1 |
| U | 13 | 13 | 0 |
| R | 19 | 16 | 3 |
| UX | 14 | 12 | 2 |
| Total | 56 | 50 | 6 |

Remaining: F8, R35, R50, R52, UX56, UX75. New source changes: PiSD 946307369b9bb47b40133bffc43ea00e7f230dc6 extracts recorder metadata and shares confirmed recording state; PiServer 96af0b698b02c96d311ef7eb58b6da9fed241865 extracts display formatting and enforces stacked STOP >=44px with four font-scale checks. New browser checks exercise actual AI toolbar start/capture/rejected stop/confirmed stop. These changes are pending exact combined CI. R35/R50/UX75 owner golden, comprehensive input and custom-theme coverage remain open. No hardware acceptance or release promotion claimed. Candidate markers unchanged.

## Previous verified continuation (superseded)

## Current verified continuation baseline

Owner-supplied accounting: 39/56 at 74ad1995200b8e2509e292d9f02e17bb9db6a905. **42/56 implemented (75.0%), 14 remaining, 4/9 batches complete** following conservative software acceptance of R36, R49 and UX54 at exact green 2a36fe323f246d7264f70dc47ff1cf058c182133. Linux [45867333772](https://github.com/henrywork059/PiDrive/actions/runs/45867333772) 4/4; Windows [45867334531](https://github.com/henrywork059/PiDrive/actions/runs/45867334531) 1/1. Actual artifact archives 15141570482 (PiSD, SHA-256 37c2612f81b89f2681f5a5bc749a0e2e1021129e3544cd1bee2770b0c9d4f6b5) and 15140788126 (PiServer, SHA-256 556ff8c256c87e4862e469f8063f1f9a625a64ee9e45c1105eedd2af9af57852) independently verified. All 78 actual Chromium matrix cases passed, including six formerly failing STOP targets and scale checks, visible sanitized event history, and task-first groups. Forward package dry runs 10/5/10 changed files passed. Selected screenshots inspected; owner-approved golden images and physical acceptance remain separate.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 9 | 1 |
| U | 13 | 13 | 0 |
| R | 19 | 16 | 3 |
| UX | 14 | 4 | 10 |
| Total | 56 | 42 | 14 |

Remaining: F8; R35, R50, R52; UX55–UX61, UX63, UX65, UX75. Active candidates unchanged: PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32. All batches authorized, but no merge, stable promotion, force push, hardware deployment, or inactive-component development.

## Current consolidated milestone (new revisions awaiting final gate)

- PiServer dcb663a817f8b863ebb65aa90272ad63e8097c40: UX58 compact telemetry default with full details available; UX59 action roles; UX60 stacked preset preview diagram; F8/R52 pure docking geometry extraction, 18 isolated parity checks. Linux 45868548716 flagged an HTML attribute-order regression; follow-up preserves original accessibility assertions and all-card geometry coverage, adds three-preset cancel verification. Exact replacement CI required.
- PiSD 84e21ff3ec1afdeaa73552b99cdb2e113419456f: UX55 medium-width preview and stacked AI layout, UX56 retain last confirmed recording status, UX57 all-value reset now draft-only until Apply. Native browser cases added; PiSD job in Linux 45868548716 passed.
- piTrainer df077eb2fd5af9240f9ff2f795bf03529a56da49: UX65 contextual status-bar help and native review/shortcut tests. Windows [45868548782](https://github.com/henrywork059/PiDrive/actions/runs/45868548782) and Linux trainer job 45868548716 passed. UX61/UX63/UX65 remain pending full replacement gate before accounting closure.
- R35/R50/UX75 retain all prior safety/accessibility/visual gates. No owner golden approval, screen-reader/physical touch or hardware acceptance claimed. No candidate version increment until complete verified milestone.

## Prior continuation record (superseded accounting)

## Current continuation baseline

Owner-supplied implementation accounting at `74ad1995200b8e2509e292d9f02e17bb9db6a905`: **39/56 implemented (69.6%), 17 remaining, 4/9 batches completed.** This is the continuation baseline, not a new CI acceptance claim. Active candidates: PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32. All remaining requirements/batches are authorized; no stable promotion, merge, force push, hardware deployment or inactive-component development authorized.

| Track | Active | Implemented baseline | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 9 | 1 |
| U | 13 | 13 | 0 |
| R | 19 | 14 | 5 |
| UX | 14 | 3 | 11 |
| Total | 56 | 39 | 17 |

Remaining: F8; R35, R36, R49, R50, R52; UX54–UX61, UX63, UX65, UX75. Batch mapping implies 1, 2, 3 and 5 complete in the supplied accounting; batches 4, 6, 7, 8 and 9 remain. No new requirement counted until its gate passes.

## Current development milestone

- Starting CI: [Linux 45817695427](https://github.com/henrywork059/PiDrive/actions/runs/45817695427) PiSD failed six narrow STOP size checks; other three jobs passed. [Windows 45817695471](https://github.com/henrywork059/PiDrive/actions/runs/45817695471) passed. Reviewed actual artifact archives 15116940071 and 15115434784; failed responsive cases terminated before final capture.
- [PiSD revision B](https://github.com/henrywork059/PiDrive/commit/50813d30b675062808fcf988a29536b40f8f4484): R36 narrow STOP hit targets, R49 visible event history, UX54 task groups, UX56 confirmed recording status, UX57 calibration presentation, R50/UX75 regression additions. Isolated Chromium 12 viewport/scale combinations passed; full integrated gate pending.
- [piTrainer revision B](https://github.com/henrywork059/PiDrive/commit/8738d4de1cdb6548ea5188e660dbe5c2c38ae978): UX61 read-only live selected-frame bulk preview. Existing UX63 stable identity comparison and UX65 contextual help retained; native acceptance pending.
- R35/R50/UX75 integrated acceptance, UX55 preview hierarchy, F8/R52 behavior-preserving extraction, UX58–UX60 operator workspace and complete cross-component gates remain open. Existing overlapping implementations must be characterized, not replaced.

Keep the implementation count at 39/56 and batches at 4/9 pending verified acceptance. See [DEVELOPMENT_SCHEDULE.md](DEVELOPMENT_SCHEDULE.md). No version increments allocated for these intermediate revisions.

---

## Historical planning audit (2026-11-24; superseded accounting)

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
