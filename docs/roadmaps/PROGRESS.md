# Active roadmap progress — 2026-11-27

## Final scoped roadmap acceptance — 2026-11-27

**56/56 active proposals implemented (100%), 0 remaining, 9/9 batches complete.** UX75 closed following explicit owner approval. Batch 4 complete. This is software-roadmap closure, not stable or physical release acceptance.

Owner explicitly approved the reviewed PiDrive web screenshot baseline on 2026-11-27 (15:41 HKT/Taipei local time), source ba2420536b733659c6cb4796490cdb38f8d31914. Approved original archives: PiSD artifact 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3; PiServer artifact 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c. Approved 105 web PNGs only (83 PiSD, 22 PiServer); original per-image manifest SHA-256 407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5. Both original archive digests and manifest rechecked independently. Preserve these exact captures for subsequent visual comparison; do not substitute later screenshots. Archive retention is finite: retain the original review archive and approval record outside CI. Approval does not cover native desktop visual review, screen readers, physical touch/hardware or stable-release promotion.

Verified exact candidate bb15dc9b18ddeac58c53e56ea4868800346f04d4, Linux [45921885146](https://github.com/henrywork059/PiDrive/actions/runs/45921885146) 4/4 and Windows [45921885201](https://github.com/henrywork059/PiDrive/actions/runs/45921885201) 1/1. Independent latest artifact downloads: PiSD 15164627462 SHA-256 4f3850f6d2f3428bcebadf25c65f3c2ab9154219f59b4c4f1b809258bd19cddc; PiServer 15163714987 SHA-256 cced837f4169f890dc2ff0d1a18c5838e9067f46a2435628c245b2e5cc32674b. Six exact-revision matrices 78/78 zero case/page errors; 67 inventories/2689 enabled control observations zero findings; 15 atomic AI geometry samples with seven panels and >=10px separation; 256 target measurements >=44px both dimensions. Forward package dry runs 15/10/11 changed files passed. Compared all 105 PNG paths against approved ba24205: no missing or new images; PiSD 62/83 and PiServer 17/22 byte-identical. Two PiSD full-page AI screenshots shorter by 16/17px, no PiServer dimension changes. Selected changed-size comparisons inspected, no production visual/runtime source changes between pinned and candidate: only fixture tools and documentation/notes. Exact approved baseline remains unchanged.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 10 | 0 |
| U | 13 | 13 | 0 |
| R | 19 | 19 | 0 |
| UX | 14 | 14 | 0 |
| Total | 56 | 56 | 0 |

UX75 complete in scoped software roadmap acceptance: repeatable visual and interaction checks cover representative happy, slow, disconnected, no-data, keyboard, touch, focus restore and responsive states; exact owner-approved web captures now pinned. R35 remains scoped automated acceptance, not exhaustive accessibility certification. All 56 active proposals and 9 batches are complete; the 19 retired exclusive proposals remain retired. Native desktop visual review, native assistive-technology verification, arbitrary custom-theme coverage, physical touch and supervised hardware acceptance remain separate. No claim of physical safety certification, frozen EXE validation, live deployment or stable acceptance. No merge, force push, stable promotion, deployment or inactive-component changes authorized. Existing candidates PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32 retained; documentation-only closure does not justify a version increment.

See [final release-candidate handover](RELEASE_CANDIDATE_HANDOVER.md) and [approved visual baseline](../ui_baseline_review.md).

## Previous verified R35 software acceptance (superseded) at 0eb91383923c521230af422bea2355ac94ff1dd9

**55/56 verified implemented (98.2%), 1 remaining, 8/9 batches complete.** R35 scoped automated acceptance complete; only UX75 remains in Batch 4.

Exact verified 0eb91383923c521230af422bea2355ac94ff1dd9: Linux [45920972375](https://github.com/henrywork059/PiDrive/actions/runs/45920972375) 4/4 after retry, Windows [45920972336](https://github.com/henrywork059/PiDrive/actions/runs/45920972336) 1/1. Initial Linux trainer job 140251362817 failed at apt update, HTTP 403 from packages.microsoft.com Ubuntu 26.04 InRelease; retried failed jobs on same source, job 140253530877 completed all Qt imports, isolated tests, clean dependencies/launchers and actual TFLite export. No workflow changes or signing/test bypass. Independently downloaded and SHA-256 matched PiSD artifact 15164224090 8c2d60218fd49009f68bea73847d215443afa9cc78528000d7b4148e28850356 and PiServer 15163813498 5d79627391c8e84ce1fef45ae2ab1685ee830d4d19888639dbaa2a410f4bd624. Six matrices exact revision, 78/78 cases, no case/page errors. All 15 atomic geometry snapshots across five sizes have seven panels and >=10px pairwise separation; original 2px overlap tolerance retained. Expanded AX inventory: PiSD 42 snapshots/1861 active independent-control observations; PiServer 25/828; total 67/2689, zero computed-name or focusability findings. 256/256 actual target measurements >=44px in both dimensions, 8/8 Manual/AI recording journeys with exact four POST requests per case. Forward-package dry runs 15/10/11 changed files passed. Windows eight native suites 40 tests passed; Linux all registered trainer regressions and smoke passed.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 10 | 0 |
| U | 13 | 13 | 0 |
| R | 19 | 19 | 0 |
| UX | 14 | 13 | 1 |
| Total | 56 | 55 | 1 |

R35 accepted in scoped automated software implementation: computed names and focusability in rendered fixture states, native keyboard and touch interactions for safe setup/non-motor workflows, visible focus including tested forced-colors states, non-color cues, reduced-motion contracts and native Qt workflow checks. No claim of exhaustive dynamic-state/tab-order coverage, arbitrary custom-theme conformance, native assistive-technology verification, physical touch or hardware safety. These remain separately tracked acceptance limitations. No genuine control defect or concurrent panel overlap reproduced; no runtime or configuration edits justified. UX75 interaction gate passes; exact owner-approved screenshot baseline still required. No explicit owner approval received. Keep pinned ba24205 web review candidate, do not replace it automatically; no trainer screenshot artifact. Current candidates PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32 unchanged. No merge, force push, stable promotion, deployment or inactive work.

## Previous inventory checkpoint (superseded, 2026-11-27)

Exact 128c69d187f8a318facae06f40e21a0e33d16c28: Linux 45916650080 3/4, Windows 45916650071 1/1. PiSD responsive AI 1440x900 case failed with 20.05px overlap from sequential bounding-box reads; measured x/width also changed. Actual simultaneous overlap is not established. PiSD artifact 15162786825 SHA-256 cd5640c4c3bf7a166182e6f05ce66ade432928e1d8b3c7b3a004ab399fcf82be and PiServer 15162259213 SHA-256 7172363081200a06f2ec8e201b46de5554a83e49ba3ce5fa148b0ed2cfc5f00b independently verified. 77/78 cases passed. Actual AX inventory 50 snapshots, 2037 enabled role observations, zero flags; additional custom focusable logs, disclosures and drive pads were named. No genuine unnamed control identified in these snapshots.

54/56 verified, 8/9 batches retained from exact green ba24205. R35 remains open until coherent geometry and expanded enforceable inventory gate pass and findings are reviewed. UX75 remains open: no explicit owner approval received. No candidate increment.

## Verified acceptance checkpoint at ba2420536b733659c6cb4796490cdb38f8d31914

**54/56 verified implemented (96.4%), 8/9 batches complete.** All previously specified primary/STOP touch targets now verified. No new requirement counted without the remaining R35 audit and UX75 baseline approval.

Exact verified source ba2420536b733659c6cb4796490cdb38f8d31914, Linux [45915971367](https://github.com/henrywork059/PiDrive/actions/runs/45915971367) 4/4 and Windows [45915971393](https://github.com/henrywork059/PiDrive/actions/runs/45915971393) 1/1. Independently verified actual archives PiSD 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3 and PiServer 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c. All six matrices, 78/78 cases, 8/8 recording journeys, no case/page errors. 256/256 actual width and height measurements >=44px (PiSD STOP 96, recording 48, dialogs 48; PiServer STOP 16, dialogs 48). Node PiSD responsive 18/18, PiServer responsive 15/15, accessibility 34/34; Windows native 40 tests, Linux trainer passed. Forward dry runs 15/10/11 changed files passed.

Independent 105-PNG comparison to 35be24a: PiSD 83 images, 56 byte-identical, eight full-page dimension increases 15–16px; PiServer 22 images, ten byte-identical, no dimension changes; none missing. Phone and landscape dialog montage independently inspected. Owner review package and manifest prepared, no images saved as approved golden. Manifest SHA-256 407e870465cbfaecd697c9c5890acc51a5fa23f5953b25027cfd87a1e46f13c5. No native Qt screenshot artifact; desktop visual approval separate.

Remaining R35: existing automated keyboard, touch, focus, named control and non-color assertions passed, but the original all-active-control audit is not yet complete. New read-only Chromium computed accessibility inventory at 45190b6ee15ba10e97a762fd4d242176563f9e78 records rendered page/dialog controls and review findings; exact CI and findings review required. This inventory cannot replace native screen-reader or physical touch/hardware review. UX75: repeatable interaction gates passed; approval of exact screenshot baseline pending. See [owner review checkpoint](../ui_baseline_review.md). Candidate markers PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32 unchanged; no version allocation, golden approval, merge, promotion or deployment.

## Previous verified checkpoint (superseded)

## Verified software implementation at 35be24a8ff55adbd50545542d2b2c3130cf814f9

**54/56 implemented (96.4%), 2 remaining, 8/9 batches complete.** UX56 and R50 accepted in scoped software implementation at exact green baseline. Batch 7 complete; Batch 4 remains open. R50 acceptance is for implemented automated regression mechanisms, not approval of golden screenshots; UX75 retains that explicit approval requirement.

Exact green baseline 35be24a8ff55adbd50545542d2b2c3130cf814f9: Linux [45914883482](https://github.com/henrywork059/PiDrive/actions/runs/45914883482) 4/4 and Windows [45914883473](https://github.com/henrywork059/PiDrive/actions/runs/45914883473) 1/1. Independently matched actual artifacts PiSD 15161413659 SHA-256 3f90798edda903730ec9c5754cd516ff0f0ac79b088c318ff2ec9bf9b48d84a7 and PiServer 15161513250 SHA-256 e0c2db2bd3adae6d48cecd0528c112984900f678f6acfd1400dc82a3f8f43ff3. Six matrices exact revision, 78/78 zero case/page errors; 8/8 Manual/AI recording journeys including all seven checkpoints, exactly four recording POST requests per journey, duplicate/stale guard and actual handler tests passed. PiSD R36 17/17, PiServer R36 14/14 and R35 34/34; all 16 stacked STOP target dimensions 44px high. Windows native Qt eight suites passed (40 tests total); Linux trainer passed. Forward dry runs PiSD/PiServer/piTrainer 15/10/11 changed files passed. Selected actual screenshots reviewed.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 10 | 0 |
| U | 13 | 13 | 0 |
| R | 19 | 18 | 1 |
| UX | 14 | 13 | 1 |
| Total | 56 | 54 | 2 |

Remaining: R35 and UX75. R35 retains comprehensive active-control keyboard/name/visible-focus and input-parity scope; no full assistive-tech/physical-touch or arbitrary custom-theme validation claimed. UX75 retains accepted screenshot baseline and integrated usability gate. Actual review found Manual Apply 26.2px at 390 width, AI Apply 26.2px and PiServer Style Save 32px. Follow-up eb61df3266caceb68225e586565b565c71e9cd63 makes selected recording/Apply/Close and style dialog actions 44px at narrow/stacked widths, verifies four scales and hit-test without mutation. Exact replacement CI required before this change is accepted. Existing candidates PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32 unchanged; no new version allocation until verified. Owner screenshot approval, physical safety and release acceptance remain separate.

## Previous verified software baseline (superseded)

## Verified software implementation at c896700c068f1d9be14c84300c1035037cdd4a3f

**52/56 implemented (92.9%), 4 remaining, 7/9 batches complete.** F8 and R52 scoped software implementation accepted at exact green parent; batch 8 complete. Previous 50/56 baseline preserved below.

Exact verified baseline c896700c068f1d9be14c84300c1035037cdd4a3f, Linux 45869995144 4/4 and Windows 45869995084 1/1. Independently matched actual artifact SHA-256: PiSD 15142042478 0b1431c45e418713b078dd0e46acd87056f8497da6585168cc30d3d0aa6baf56; PiServer 15142681656 9533e6a19e1868805e1bf5afa0b701f5d775c110ed8c9f77539b86f3cb03b91c. All 78 matrix cases exact revision, zero errors. Selected actual screenshots reviewed. Forward-package dry runs 14/10/11 changed files passed. PiSD recording storage 4/4, responsive Node 16/16, AI toolbar four actual journeys passed; PiServer responsive 14/14, accessibility 34/34 and all 16 stacked STOP font-scale measurements 44px. Native trainer review-context 7/7 and validation-to-data 5/5 on both OS. Prior isolated formatter/docking parity and metadata characterization tests passed; existing route/config/launch interfaces unchanged.

| Track | Active | Verified implementation | Remaining |
| --- | ---: | ---: | ---: |
| F | 10 | 10 | 0 |
| U | 13 | 13 | 0 |
| R | 19 | 17 | 2 |
| UX | 14 | 12 | 2 |
| Total | 56 | 52 | 4 |

Remaining: R35, R50, UX56, UX75. Batch 4 and 7 remain open. PiSD 4301c00fe420d5c03aeed41386fbe5ed1b186d10 implements immediate recording acknowledgement, duplicate request suppression, stale/out-of-order recording read rejection and idle confirmed recording polling; subsequent accessibility metadata and actual Manual/AI idle/status workflow checks pending exact CI. R35/R50/UX75 retain original scope: automated tests are extensive, but owner approved baseline/golden visual review and remaining comprehensive input/assistive-technology/custom-theme acceptance are not asserted. Physical hardware and release approval separate. Current candidate markers remain PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32; do not allocate new versions on unverified code.

## Previous verified software baseline (superseded)

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


## Main integration reconciliation — 2026-11-27

The owner explicitly requested merging all open PiDrive PRs into main. All 24 open PR heads (#45, #46, #49, #50, #53, #54, #55, #56, #59, #61, #63, #64, #66, #67, #69, #72, #73, #75, #76, #78, #82, #83, #86, #87) were individually verified as ancestors of, or equal to, the exact green completed candidate 6aaee7050485a6b1c3f841cd5837db8be4820768. Linux [45960538086](https://github.com/henrywork059/PiDrive/actions/runs/45960538086) 4/4 and Windows [45960538133](https://github.com/henrywork059/PiDrive/actions/runs/45960538133) 1/1 passed. No independent replay of older patches is required.

Previous main 8dfae027ae200757f6adf7669ea8a9b84b8db884 and the completed candidate diverged from c615c73032d62daa23ec0fe302d1cfe6049428c3. Complete recursive Git blob inventories showed no main-only file changes, two identically changed files and five differing documentation paths; 322 candidate-only changed paths. Retain the final candidate's software, version markers, tests, and 56/56 / 9/9 accounting; preserve all previous main commits as the second parent of this reconciliation. Historical main documents remain accessible at the immutable [progress snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/PROGRESS.md), [schedule snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/DEVELOPMENT_SCHEDULE.md), [README](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/README.md), [roadmap index](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/README.md) and [acceptance record](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/stabilization_acceptance.md). Older progress counts are superseded, not deleted from history.

The candidate-first merge-parent order preserves the version-changing first-parent history used by tools/check_forward_packages.py. Integrate by a normal non-forced fast-forward of main to the reconciliation commit, only while both source references remain as verified. No production source, configuration, regression, version marker, retired component, or approved visual baseline changes in this reconciliation. Merge authorization does not imply stable promotion, hardware deployment, native desktop visual or assistive-technology approval. No release tag or new version. Verify final main and its CI separately.
