# Consolidated active development schedule — 2026-11-24

This is the current execution plan, replacing one-proposal-at-a-time scheduling. It retains every outstanding original active proposal and all earlier accepted improvements. The original four roadmap documents remain historical requirements; their IDs are not renumbered.

## Scope and accounting

- Active: PiSD, PiServer, piTrainer. No new PiBooter/CustomTrainer/CustomDrive or legacy piCar work.
- Original proposals: 75; retired exclusive proposals: 19; active: 56.
- As of the current [progress audit](PROGRESS.md): 35 implemented, 5 partial, 16 without a dedicated update. **21 original proposal IDs remain** in **6 remaining development batches** (9 batches originally scheduled, 3 complete). The former PiBooter batch is removed; R48 remains implemented for the active runtimes.
- Batch numbers are planning units, not component versions, PR numbers, or calendar deadlines. Deliver related work together where safe, using separate component-owned commits, patch notes and patch-only archives when requested. No monolithic cross-component source rewrite.
- Sequence is dependency- and acceptance-gated, not an invented time estimate. Independent work may proceed once its stated prerequisites are met; no unsafe parallel release or merging without authorization.

## Current starting point

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) is the original green active integration baseline. [PR #87](https://github.com/henrywork059/PiDrive/pull/87) completes Batch 1 (F2, F3, F4, U21) and Batch 2 (F7, UX74). Batch 3 (F9/R53) passed all four jobs in [CI 45380631288](https://github.com/henrywork059/PiDrive/actions/runs/45380631288) at 53b06b7. Batch 4 started at [793b3e2](https://github.com/henrywork059/PiDrive/commit/793b3e25b3100b05da0454ea3da56cf892f77aad): PiSD 0.11.29, PiServer 0.4.32, piTrainer 0.11.13. Initial [CI 45383964152](https://github.com/henrywork059/PiDrive/actions/runs/45383964152) passed 3/4; real browser tests identified Manual Drive startup ReferenceError. Corrected at [299960b](https://github.com/henrywork059/PiDrive/commit/299960b5bcefb033d85c8955087822802429e14a), strengthened readback and dialog geometry checks; [CI 45384279829](https://github.com/henrywork059/PiDrive/actions/runs/45384279829) passed all four jobs (16/16 browser cases). R45 complete. New [d134c19](https://github.com/henrywork059/PiDrive/commit/d134c1970786e6c8b1071ab6a9e49936da84821d), PiSD 0.11.30, adds dialog focus and extended native tests; [CI 45396916022](https://github.com/henrywork059/PiDrive/actions/runs/45396916022) exposed splitter restoration and a PiServer fixture assumption; corrected at 7d024cd (piTrainer 0.11.14) and 300f018. Final [CI 45397236501](https://github.com/henrywork059/PiDrive/actions/runs/45397236501) completed successfully at 300f018: PiSD, PiServer, piTrainer and manifest compatibility all passed; 16/16 Chromium viewport cases and the corrected native Qt splitter regression passed. Following verified 300f018, [ba21198](https://github.com/henrywork059/PiDrive/commit/ba21198cda8a5d7a38e2dc6de8bdb9cbdc943d07) added truthful rejected Settings STOP feedback in PiSD 0.11.31 and Save retry/error browser tests; [CI 45415572994](https://github.com/henrywork059/PiDrive/actions/runs/45415572994) passed all four jobs. Actual baseline screenshots then exposed PiServer metric-card clipping; [ffa507d](https://github.com/henrywork059/PiDrive/commit/ffa507d48cda5aaba06007c5afdf5e717c315fa5) corrected intrinsic scrollable Status card rows in PiServer 0.4.33 with overflow assertions. [CI 45416643320](https://github.com/henrywork059/PiDrive/actions/runs/45416643320) passed all four jobs. A selected 390px and 1440px PiServer screenshot comparison confirms the prior overlap was resolved; explicit owner golden approval and full interaction acceptance remain pending. Next [1731528](https://github.com/henrywork059/PiDrive/commit/1731528ca5b59df795493a838f25dcd67840dca5) (piTrainer 0.11.15) resets stale edited-frame markers on a fresh validation result, retains same-result refresh markers and adds native Qt source/mirror, session-collision and selected-frame sort/return tests. [CI 45418879933](https://github.com/henrywork059/PiDrive/actions/runs/45418879933) passed all four jobs, including the new tests and clean dependency smoke. After that, [89d779d](https://github.com/henrywork059/PiDrive/commit/89d779de673b71198a5fd01c36b20334561528da) (piTrainer 0.11.16) re-resolves a synthetic validation frame's original after its previously unloaded session enters Data. First [CI 45420759869](https://github.com/henrywork059/PiDrive/actions/runs/45420759869) failed new native test collection due to the minimal CI test environment omitting already-declared matplotlib. [7c7bf08](https://github.com/henrywork059/PiDrive/commit/7c7bf088675976c678ea66ef4feb2fb030838b12) corrected isolated test dependencies without weakening the test; [CI 45421065674](https://github.com/henrywork059/PiDrive/actions/runs/45421065674) passed all four jobs, including both new integrated Qt cases and clean desktop/full dependency smoke. Next [3e0663b](https://github.com/henrywork059/PiDrive/commit/3e0663bb4e33ee29f4a2d7562f89195f64fe46ae) (piTrainer 0.11.17) adds confirmed pending label-edit flush before application close, retains failed edits for retry, blocks close on unconfirmed metadata save and adds full Validate→Data→source-label save→Validate return tests. First [CI 45424069356](https://github.com/henrywork059/PiDrive/actions/runs/45424069356) passed four of five new Qt cases; one CloseHarness fixture failed due to an uninitialized responsive-density helper in that minimal subclass. Test-only [fd5bc3e](https://github.com/henrywork059/PiDrive/commit/fd5bc3e855d07791c7aca6dc52ecdc4956012b1a) isolated the close-event test; [CI 45424414919](https://github.com/henrywork059/PiDrive/actions/runs/45424414919) passed all four jobs, including all five native Qt cases. Pandas FutureWarnings remain nonblocking and separately recorded. Next [b379138](https://github.com/henrywork059/PiDrive/commit/b379138744b952a6203c2f6a29c458e3b6a59ea1) (piTrainer 0.11.18) fixes nonzero soft-minimum splitter allocation: user-saved ratios of whole panels were incorrectly applied only to free pixels after fixed minimums. New constrained allocator honors preferred proportions whenever feasible, freezes only panels under existing soft minimums, and preserves old below-minimum fallback and QSettings layout schema. Exact [CI 45426094777](https://github.com/henrywork059/PiDrive/actions/runs/45426094777) passed all four jobs and four new native Qt preset/narrow-screen/restore tests (zero skipped), plus clean dependency/launcher smoke. No candidate runtime merged or physically validated. See [PROGRESS.md](PROGRESS.md) for evidence and limits. Reconcile canonical main-branch roadmap before merging a candidate.

## Batch sequence

| Batch | Priority | Focus | Original IDs | Remaining | Prerequisites |
| --- | --- | --- | --- | ---: | --- |
| 1 | P0 | Runtime safety and validation | F2, F3, F4, U21 | 0 | Green PR #86 baseline |
| 2 | P1 | Configuration and data protection | F7, UX74 | 0 | 1 |
| 3 | P1 | Release automation and anti-rollback | F9, R53 | 0 | 1–2 |
| 4 | P1 | UI regression and accessibility foundation | R35, R36, R45, R50, UX75 | 4 | 1–3 |
| 5 | P1 | Training and deployment integration | F10, R51, UX62, UX64 | 4 | 1–4 |
| 6 | P1 | piTrainer data-review workflow | UX61, UX63, UX65 | 3 | 4, 5 |
| 7 | P1/P2 | PiSD driving interface | R49, UX54, UX55, UX56, UX57 | 5 | 1, 2, 4 |
| 8 | P2 | Code modularization | F8, R52 | 2 | 1–4; rerun tests from completed batches |
| 9 | P1/P2 | PiServer operator workspace | UX58, UX59, UX60 | 3 | 4, 8 |
| Total | | | | 21 | |

### Batch 1 — Runtime safety and validation

**Components:** PiSD, PiServer. **Status:** Complete at scoped automated implementation gate (F2, F3, F4, U21). Physical acceptance remains separate.

**Scope:** Finish the two PiSD standalone validation commands (F4); implement and test PiSD's server-side manual command lease/watchdog (F2); add PiSD LAN authorization/access protection with authorized STOP and explicit compatibility guidance (F3); audit and complete PiServer stale-camera autonomous-motion stop/rearm (U21). Separate each safety concern into a reviewable commit/subpatch.

**Acceptance gate:** Both full simulation validation commands pass; fake-clock timeout/dropout and authorized/unauthorized control tests; stale-frame and explicit rearm tests; no STOP regression. Supervised Pi hardware safety acceptance remains a separate release gate.

### Batch 2 — Configuration and data protection

**Components:** All active components, where applicable. **Status:** Complete at scoped automated implementation gate (F7, UX74); real-browser and Windows acceptance remain separate.

**Scope:** Complete corrupt-config preservation and recovery warnings in affected active runtimes; retain recovery copies, safe normalization and round trips. Pair with clear destructive-action confirmations, exact targets, duplicate-submit protection and truthful undo availability in each applicable interface. Never confirmation-gate emergency STOP.

**Acceptance gate:** Malformed-file and restart tests, original bytes preserved, exact deletion targets, no accidental data/config overwrites, no STOP delay.

### Batch 3 — Release automation and anti-rollback

**Components:** Monorepo / three active components. **Status:** Complete at scoped automated implementation gate (CI 45380631288, all four jobs).

**Scope:** Align dependency groups and launch instructions; add changed-file-only package manifests, base identifiers, hashes, allowed paths, cache/user-data exclusions and dry-run validation against accepted baseline and latest plus three preceding notes. Do not move components or modify persistent user settings.

**Acceptance gate:** Clean dependency smoke checks; package validation accepts intended patch and rejects stale/wrong-component/extra-file packages; notes report actual tests.

### Batch 4 — UI regression and accessibility foundation

**Components:** All active interfaces. **Status:** In progress; R45 complete. Latest candidate b379138 (PiSD 0.11.31 / PiServer 0.4.33 / piTrainer 0.11.18) passed CI 45426094777 (4/4 jobs), including four new native Qt realistic workspace minimum-size cases and existing label-save/close coverage. Rejected Settings Save/Retry/STOP feedback and Status metric intrinsic sizing are covered at all browser widths. Selected PiServer screenshots reviewed (390 and 1440 px), but full active-control audit, owner-approved golden captures, slow/disconnected journeys, native Windows/owner visual acceptance and broader real desktop accessibility remain outstanding; nonzero-minimum Qt and exact allocation tests now pass.

**Scope:** Finish desktop accessibility audit and PiSD token/drift coverage; add native Qt and browser interaction/geometry smoke tests covering keyboard, touch, focus, no-data, failures and 390/768/1024/1440 widths. Record accepted baseline captures before visual changes. Use this suite for subsequent UI batches.

**Acceptance gate:** Existing layout and controls preserved; STOP and Save reachable; stable frame selection, splitter/focus behavior; baseline images reviewed separately from automated checks.

### Batch 5 — Training and deployment integration

**Components:** PiSD, piTrainer, PiServer. **Status:** Planned.

**Scope:** Synthetic current/legacy recording fixtures, label edit/hidden/flip/export contracts; link recording, preprocess, training, validation, export and loaded model provenance without invented historical fields; add compact tab readiness markers and readable plot/run/artifact context.

**Acceptance gate:** Deterministic recording-to-model contract tests, preserved model family/checksum checks, missing-link handling, no overwritten artifacts or altered six-tab order. Actual training/deployment acceptance separate.

### Batch 6 — piTrainer data-review workflow

**Components:** piTrainer. **Status:** Planned.

**Scope:** Contextual bulk-edit preview with exact count and representative old/new values; synchronized label/prediction comparison keyed to stable source-frame identity; contextual keyboard help without intercepting text entry. Preserve all 0.11.10 selection fixes and existing edit/hide/delete shortcuts.

**Acceptance gate:** Native Qt tests for sort/filter/selection/validation return, exact mutation scope, compare identity, playback and shortcut behavior.

### Batch 7 — PiSD driving interface

**Components:** PiSD. **Status:** Planned.

**Scope:** Finish sanitized bounded recent operator events; task-first front page; preview-first hierarchy with status and STOP reachable; recording mini-toolbar using confirmed counters/outcomes; geometry/appearance calibration grouping with scoped reset.

**Acceptance gate:** No raw secrets in events, no automatic arming, no duplicate safety acknowledgement, unchanged overlay calibration/defaults and saved recording format; responsive smoke tests.

### Batch 8 — Code modularization

**Components:** Affected active modules, especially PiServer. **Status:** Planned.

**Scope:** Characterize behavior before extracting pure parsing, formatting, validation and controller/DOM helpers. Keep stable public APIs, config paths, component boundaries and launchers. Prefer small staged extractions rather than a rewrite.

**Acceptance gate:** Characterization and regression parity; no changed route or config semantics, no lost shortcuts/layout/previous fixes.

### Batch 9 — PiServer operator workspace

**Components:** PiServer. **Status:** Planned.

**Scope:** Tier status telemetry with essentials visible, distinguish hardware actions from layout and destructive actions, add non-destructive Driving/Camera tuning/Model testing presets with preview/cancel. Retain saved custom layout and theme.

**Acceptance gate:** Responsive and keyboard checks, existing motor/camera/STOP behavior, saved layout survives cancel/restart; only explicit save replaces user layout.

## Execution and reporting rules

1. Inspect the live branch and latest plus three prior component notes before editing; start from the latest accepted/integrated state. Do not overwrite with older ZIP contents.
2. Characterize any overlapping already-implemented functionality before changing it. Implement only the remaining active portions of each proposal.
3. Keep safety, authorization and hardware-control changes independently reviewable and testable even when scheduled as one batch. Preserve the previously green candidate until the replacement passes.
4. Run the affected component tests and full active regression gate. Record simulation/browser/Qt/Windows/physical hardware verification separately; do not weaken tests to obtain green status.
5. For each completed batch update PROGRESS.md with per-ID evidence, remaining original IDs, completed/remaining batches, actual component versions and CI links. A batch is complete only when every included active proposal meets its scoped implementation/verification gate; partial completion decreases the proposal count only as justified by evidence.
6. Keep release/merge authorization and physical acceptance separate. No calendar delivery dates or version numbers assigned before implementation.
