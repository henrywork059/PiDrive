# Consolidated active development schedule — 2026-11-24

This is the current execution plan, replacing one-proposal-at-a-time scheduling. It retains every outstanding original active proposal and all earlier accepted improvements. The original four roadmap documents remain historical requirements; their IDs are not renumbered.

## Scope and accounting

- Active: PiSD, PiServer, piTrainer. No new PiBooter/CustomTrainer/CustomDrive or legacy piCar work.
- Original proposals: 75; retired exclusive proposals: 19; active: 56.
- As of the current [progress audit](PROGRESS.md): 35 implemented, 21 partial/candidate, 0 without a dedicated update. **21 original proposal IDs remain** in **6 remaining development batches** (9 batches originally scheduled, 3 complete). The former PiBooter batch is removed; R48 remains implemented for the active runtimes.
- Batch numbers are planning units, not component versions, PR numbers, or calendar deadlines. Deliver related work together where safe, using separate component-owned commits, patch notes and patch-only archives when requested. No monolithic cross-component source rewrite.
- Sequence is dependency- and acceptance-gated, not an invented time estimate. Independent work may proceed once its stated prerequisites are met; no unsafe parallel release or merging without authorization.

## Current starting point

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) is the original green active integration baseline. [PR #87](https://github.com/henrywork059/PiDrive/pull/87) completes Batch 1 (F2, F3, F4, U21) and Batch 2 (F7, UX74). Batch 3 (F9/R53) passed all four jobs in [CI 45380631288](https://github.com/henrywork059/PiDrive/actions/runs/45380631288) at 53b06b7. Batch 4 started at [793b3e2](https://github.com/henrywork059/PiDrive/commit/793b3e25b3100b05da0454ea3da56cf892f77aad): PiSD 0.11.29, PiServer 0.4.32, piTrainer 0.11.13. Initial [CI 45383964152](https://github.com/henrywork059/PiDrive/actions/runs/45383964152) passed 3/4; real browser tests identified Manual Drive startup ReferenceError. Corrected at [299960b](https://github.com/henrywork059/PiDrive/commit/299960b5bcefb033d85c8955087822802429e14a), strengthened readback and dialog geometry checks; [CI 45384279829](https://github.com/henrywork059/PiDrive/actions/runs/45384279829) passed all four jobs (16/16 browser cases). R45 complete. New [d134c19](https://github.com/henrywork059/PiDrive/commit/d134c1970786e6c8b1071ab6a9e49936da84821d), PiSD 0.11.30, adds dialog focus and extended native tests; [CI 45396916022](https://github.com/henrywork059/PiDrive/actions/runs/45396916022) exposed splitter restoration and a PiServer fixture assumption; corrected at 7d024cd (piTrainer 0.11.14) and 300f018. Final [CI 45397236501](https://github.com/henrywork059/PiDrive/actions/runs/45397236501) completed successfully at 300f018: PiSD, PiServer, piTrainer and manifest compatibility all passed; 16/16 Chromium viewport cases and the corrected native Qt splitter regression passed. Following verified 300f018, [ba21198](https://github.com/henrywork059/PiDrive/commit/ba21198cda8a5d7a38e2dc6de8bdb9cbdc943d07) added truthful rejected Settings STOP feedback in PiSD 0.11.31 and Save retry/error browser tests; [CI 45415572994](https://github.com/henrywork059/PiDrive/actions/runs/45415572994) passed all four jobs. Actual baseline screenshots then exposed PiServer metric-card clipping; [ffa507d](https://github.com/henrywork059/PiDrive/commit/ffa507d48cda5aaba06007c5afdf5e717c315fa5) corrected intrinsic scrollable Status card rows in PiServer 0.4.33 with overflow assertions. [CI 45416643320](https://github.com/henrywork059/PiDrive/actions/runs/45416643320) passed all four jobs. A selected 390px and 1440px PiServer screenshot comparison confirms the prior overlap was resolved; explicit owner golden approval and full interaction acceptance remain pending. Next [1731528](https://github.com/henrywork059/PiDrive/commit/1731528ca5b59df795493a838f25dcd67840dca5) (piTrainer 0.11.15) resets stale edited-frame markers on a fresh validation result, retains same-result refresh markers and adds native Qt source/mirror, session-collision and selected-frame sort/return tests. [CI 45418879933](https://github.com/henrywork059/PiDrive/actions/runs/45418879933) passed all four jobs, including the new tests and clean dependency smoke. After that, [89d779d](https://github.com/henrywork059/PiDrive/commit/89d779de673b71198a5fd01c36b20334561528da) (piTrainer 0.11.16) re-resolves a synthetic validation frame's original after its previously unloaded session enters Data. First [CI 45420759869](https://github.com/henrywork059/PiDrive/actions/runs/45420759869) failed new native test collection due to the minimal CI test environment omitting already-declared matplotlib. [7c7bf08](https://github.com/henrywork059/PiDrive/commit/7c7bf088675976c678ea66ef4feb2fb030838b12) corrected isolated test dependencies without weakening the test; [CI 45421065674](https://github.com/henrywork059/PiDrive/actions/runs/45421065674) passed all four jobs, including both new integrated Qt cases and clean desktop/full dependency smoke. Next [3e0663b](https://github.com/henrywork059/PiDrive/commit/3e0663bb4e33ee29f4a2d7562f89195f64fe46ae) (piTrainer 0.11.17) adds confirmed pending label-edit flush before application close, retains failed edits for retry, blocks close on unconfirmed metadata save and adds full Validate→Data→source-label save→Validate return tests. First [CI 45424069356](https://github.com/henrywork059/PiDrive/actions/runs/45424069356) passed four of five new Qt cases; one CloseHarness fixture failed due to an uninitialized responsive-density helper in that minimal subclass. Test-only [fd5bc3e](https://github.com/henrywork059/PiDrive/commit/fd5bc3e855d07791c7aca6dc52ecdc4956012b1a) isolated the close-event test; [CI 45424414919](https://github.com/henrywork059/PiDrive/actions/runs/45424414919) passed all four jobs, including all five native Qt cases. Pandas FutureWarnings remain nonblocking and separately recorded. Next [b379138](https://github.com/henrywork059/PiDrive/commit/b379138744b952a6203c2f6a29c458e3b6a59ea1) (piTrainer 0.11.18) fixes nonzero soft-minimum splitter allocation: user-saved ratios of whole panels were incorrectly applied only to free pixels after fixed minimums. New constrained allocator honors preferred proportions whenever feasible, freezes only panels under existing soft minimums, and preserves old below-minimum fallback and QSettings layout schema. Exact [CI 45426094777](https://github.com/henrywork059/PiDrive/actions/runs/45426094777) passed all four jobs and four new native Qt preset/narrow-screen/restore tests (zero skipped), plus clean dependency/launcher smoke. Next [7fba71c](https://github.com/henrywork059/PiDrive/commit/7fba71c4e7daa5f8611224291b32dbdbfbd32708) (PiServer 0.4.34) fixes an initial read rejection aborting all status polling, marks unknown dashboard telemetry and E-STOP state as unverified and ensures unverified E-STOP cannot request rearm. [CI 45431856457](https://github.com/henrywork059/PiDrive/actions/runs/45431856457) passed all four jobs, including synthetic read-only 503 startup, STOP-only submission and recovery at four Chromium widths. No endpoint/motor-service behavior changed. Next [05c242f](https://github.com/henrywork059/PiDrive/commit/05c242fb8b70e259363a3c1e8e9a8865f21820e3) (PiServer 0.4.35) adds a 3500ms browser-side timeout only for un-signaled read-only GETs; a hanging startup model GET or status GET can no longer block initialization or hold the status single-flight guard forever. Mutation POSTs, especially E-STOP, remain untouched because cancellation cannot confirm server-side outcome. [CI 45433987366](https://github.com/henrywork059/PiDrive/actions/runs/45433987366) passed all four jobs with actual Chromium pending-request timeout, retry, STOP-only and recovery cases passing at 390/768/1024/1440px; no browser page errors. No candidate runtime merged or physically validated. [e679901](https://github.com/henrywork059/PiDrive/commit/e67990148ba1424a9cd2059425178567eaf56499) (PiServer 0.4.36) protects the dashboard from superseded status GET successes/failures after a newer confirmed snapshot, without changing STOP/rearm semantics or the 3500ms read-only timeout. [CI 45438129785](https://github.com/henrywork059/PiDrive/actions/runs/45438129785) passed all four jobs; three new JS ordering tests and four Chromium viewport cases passed, including held pre-STOP GET, synthetic STOP acknowledgement and subsequent fresh recovery. All mutations intercepted; no physical actuation, Windows or owner golden acceptance. Progress remains 35/56; Batch 4 remains open. See [PROGRESS.md](PROGRESS.md) for evidence and limits. Reconcile canonical main-branch roadmap before merging a candidate.

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

**Components:** All active interfaces. **Status:** In progress; R45 complete. Latest fully verified candidate at inspection: 174026c (PiSD 0.11.33 / PiServer 0.4.41 / piTrainer 0.11.21). See combined evidence below. Saved-folder response ordering regression passed. Previous 7ec1be7 passed CI 45517818839 (4/4 jobs). Recording/snapshot acknowledgement recovery and failed folder-read feedback passed the regression gate. Previous 6b782f7 passed CI 45515079463 (4/4 jobs). Model-library explicit Refresh failure/retry and selection retention/fallback passed all four Chromium widths. The real Chromium PiServer tests now cover both disconnected HTTP 503 startup/recovery and genuinely pending GETs bounded by read-only timeouts, preserving STOP-only behavior while status is unverified at all four viewport widths; native Qt layout and label-save/close tests remain green. Rejected Settings Save/Retry/STOP feedback and Status metric intrinsic sizing are covered at all browser widths. Selected PiServer screenshots reviewed (390 and 1440 px), but full active-control audit, owner-approved golden captures, other slow-request and disconnected journeys, owner visual acceptance and broader desktop accessibility remain outstanding. PiServer synthetic HTTP 503, indefinitely pending GET, superseded delayed status replies after a newer acknowledgement, and recovered-state paths, plus nonzero-minimum Qt layout tests now pass.

**Scope:** Finish desktop accessibility audit and PiSD token/drift coverage; add native Qt and browser interaction/geometry smoke tests covering keyboard, touch, focus, no-data, failures and 390/768/1024/1440 widths. Record accepted baseline captures before visual changes. Use this suite for subsequent UI batches.

**Acceptance gate:** Existing layout and controls preserved; STOP and Save reachable; stable frame selection, splitter/focus behavior; baseline images reviewed separately from automated checks.

### Batch 5 — Training and deployment integration

**Components:** PiSD, piTrainer, PiServer. **Status:** Candidate implementation advanced through piTrainer 0.11.21; dependent Batch 4 acceptance remains open. No proposal closure.

**Scope:** Synthetic current/legacy recording fixtures, label edit/hidden/flip/export contracts; link recording, preprocess, training, validation, export and loaded model provenance without invented historical fields; add compact tab readiness markers and readable plot/run/artifact context.

**Acceptance gate:** Deterministic recording-to-model contract tests, preserved model family/checksum checks, missing-link handling, no overwritten artifacts or altered six-tab order. Actual training/deployment acceptance separate.

### Batch 6 — piTrainer data-review workflow

**Components:** piTrainer. **Status:** Forward candidate committed; remaining acceptance open (see combined evidence below).

**Scope:** Contextual bulk-edit preview with exact count and representative old/new values; synchronized label/prediction comparison keyed to stable source-frame identity; contextual keyboard help without intercepting text entry. Preserve all 0.11.10 selection fixes and existing edit/hide/delete shortcuts.

**Acceptance gate:** Native Qt tests for sort/filter/selection/validation return, exact mutation scope, compare identity, playback and shortcut behavior.

### Batch 7 — PiSD driving interface

**Components:** PiSD. **Status:** Forward candidate committed; remaining acceptance open (see combined evidence below).

**Scope:** Finish sanitized bounded recent operator events; task-first front page; preview-first hierarchy with status and STOP reachable; recording mini-toolbar using confirmed counters/outcomes; geometry/appearance calibration grouping with scoped reset.

**Acceptance gate:** No raw secrets in events, no automatic arming, no duplicate safety acknowledgement, unchanged overlay calibration/defaults and saved recording format; responsive smoke tests.

### Batch 8 — Code modularization

**Components:** Affected active modules, especially PiServer. **Status:** Forward candidate committed; remaining acceptance open (see combined evidence below).

**Scope:** Characterize behavior before extracting pure parsing, formatting, validation and controller/DOM helpers. Keep stable public APIs, config paths, component boundaries and launchers. Prefer small staged extractions rather than a rewrite.

**Acceptance gate:** Characterization and regression parity; no changed route or config semantics, no lost shortcuts/layout/previous fixes.

### Batch 9 — PiServer operator workspace

**Components:** PiServer. **Status:** Forward candidate committed; remaining acceptance open (see combined evidence below).

**Scope:** Tier status telemetry with essentials visible, distinguish hardware actions from layout and destructive actions, add non-destructive Driving/Camera tuning/Model testing presets with preview/cancel. Retain saved custom layout and theme.

**Acceptance gate:** Responsive and keyboard checks, existing motor/camera/STOP behavior, saved layout survives cancel/restart; only explicit save replaces user layout.

[7ec1be7](https://github.com/henrywork059/PiDrive/commit/7ec1be78cc5d1d7fcefcaa768dd79e6365b1d024) (PiServer 0.4.38) separates recording/snapshot POST acknowledgement from failed optional folder GET, preserves confirmed recording state and status polling, and adds accessible partial-success feedback. [CI 45517818839](https://github.com/henrywork059/PiDrive/actions/runs/45517818839) completed successfully, all four jobs passed, including six registered recording-feedback JS cases and native Chromium fixture at four widths. No physical hardware, owner visual or Windows acceptance; no count increment.

[8aabfef](https://github.com/henrywork059/PiDrive/commit/8aabfef9efec8dfdac373aa3f97f1ebf9207e2b4) (PiServer 0.4.39) passed [CI 45518657406](https://github.com/henrywork059/PiDrive/actions/runs/45518657406), all four jobs. Nine saved-folder ordering cases cover selection at response, superseded success/failure and acknowledged deletion. Batch 4 still requires full active-control and owner visual acceptance.

[581c049](https://github.com/henrywork059/PiDrive/commit/581c049154e06bb56d1ac671af9020729b370a65) advances piTrainer 0.11.19 with Batch 4/5 candidate work: validation accessible names, real-file-only TFLite selection, six-tab advisory input readiness, validation dataset/run/checksum context, mixed on-disk recording-to-dummy-export tests, four-width PiServer held-folder/acknowledged deletion scenario, and separate hosted native Windows Qt workflow. Exact candidate Linux and hosted Windows CI passed; owner visual acceptance and remaining Batch 5 work pending. No proposal closure. No actual training, physical deployment, or runtime merge.


## Batches 4–9 — combined forward candidates (2026-11-25)

Prior exact head [581c049](https://github.com/henrywork059/PiDrive/commit/581c049154e06bb56d1ac671af9020729b370a65) passed [Linux 45531850972](https://github.com/henrywork059/PiDrive/actions/runs/45531850972) (4/4) and [Windows native Qt 45531851593](https://github.com/henrywork059/PiDrive/actions/runs/45531851593) (1/1). Hosted Windows automated acceptance is now verified; owner visual acceptance is not. [PiSD captures](https://github.com/henrywork059/PiDrive/actions/runs/45531850972/artifacts/14985247338) and [PiServer captures](https://github.com/henrywork059/PiDrive/actions/runs/45531850972/artifacts/14985177533) are review artifacts, not approved golden baselines.

- [a36e193](https://github.com/henrywork059/PiDrive/commit/a36e193c011053ebda60e84d40be464bc0895cae), piTrainer 0.11.20: selected-row bulk-edit preview, finite same-frame label/prediction comparison and live edit delta, validation plot context, contextual F1 help, focused helper tests.
- [60be150](https://github.com/henrywork059/PiDrive/commit/60be150c39e21aca03ed0dc8254a28bb84ca22c6), PiSD 0.11.32: bounded allowlisted local event history, read/copy interface, task-first landing page and prominent STOP, confirmed recording count, scoped calibration draft resets.
- [821def6](https://github.com/henrywork059/PiDrive/commit/821def6680f437b7e3afe5bddb42515fcd7f4c33), PiServer 0.4.40: local layout module, preset preview/cancel/save, essentials-only status toggle, four-width browser tests; also corrects PiSD alignment reset keys to existing base_y/horizon_y. Preset preview never switches operating mode. Prior custom layout, hardware routes and existing drag autosave outside preview retained.

Exact current head: 821def6680f437b7e3afe5bddb42515fcd7f4c33. [Linux CI 45538852480](https://github.com/henrywork059/PiDrive/actions/runs/45538852480): in_progress (Trainer-to-runtime manifest compatibility: success; PiServer regression: in_progress; PiSD regression: success; piTrainer regression: success). [Windows CI 45538852452](https://github.com/henrywork059/PiDrive/actions/runs/45538852452): success. Last fully green candidate at inspection: 581c049 (PiSD 0.11.31 / PiServer 0.4.39 / piTrainer 0.11.19).

Remaining acceptance: R35/R36/R50/UX75 comprehensive active-control audit and owner screenshot approval; F10 actual output-order/runtime fixture expansion, R51 portable recording-to-loaded-model provenance and stale training-run association handling, UX62 readiness completion states, UX64 training/export artifact context; UX61/63/65 broader native selection/mutation/shortcut checks; R49 browser copy/STOP history checks, UX54–57 front/preview/recording/calibration interaction and visual acceptance; F8/R52 further characterized modular extraction; UX58–60 full operator workspace keyboard, responsive, layout reload and visual review. No physical testing, real training, deployment or runtime merge. All outstanding batches have candidate work, but acceptance is not complete. Conservative accepted implementation count remains 35/56; 21 outstanding. Candidate diff from 581c049: three forward commits, 27 files added/modified, no file deletions or inactive component changes.

## Execution and reporting rules

1. Inspect the live branch and latest plus three prior component notes before editing; start from the latest accepted/integrated state. Do not overwrite with older ZIP contents.
2. Characterize any overlapping already-implemented functionality before changing it. Implement only the remaining active portions of each proposal.
3. Keep safety, authorization and hardware-control changes independently reviewable and testable even when scheduled as one batch. Preserve the previously green candidate until the replacement passes.
4. Run the affected component tests and full active regression gate. Record simulation/browser/Qt/Windows/physical hardware verification separately; do not weaken tests to obtain green status.
5. For each completed batch update PROGRESS.md with per-ID evidence, remaining original IDs, completed/remaining batches, actual component versions and CI links. A batch is complete only when every included active proposal meets its scoped implementation/verification gate; partial completion decreases the proposal count only as justified by evidence.
6. Keep release/merge authorization and physical acceptance separate. No calendar delivery dates or version numbers assigned before implementation.

## 2026-11-25 — forward batch implementation and verification

- 821def6: Linux CI [45538852480](https://github.com/henrywork059/PiDrive/actions/runs/45538852480) failed the PiServer browser density-checkbox interaction at all four widths; the other three Linux jobs and native Windows Qt passed.
- [b641f02](https://github.com/henrywork059/PiDrive/commit/b641f02635889d8773b7cc88a5bd04a9a8babf4d) fixes the Status grid obstruction with a scrollable intrinsic-height column and actual pointer/Space interaction assertions. Exact [Linux 45554836806](https://github.com/henrywork059/PiDrive/actions/runs/45554836806) 4/4 and [Windows 45554836817](https://github.com/henrywork059/PiDrive/actions/runs/45554836817) 1/1 completed successfully. Last fully verified versions: PiSD 0.11.32, PiServer 0.4.40, piTrainer 0.11.20.
- [acf80cd](https://github.com/henrywork059/PiDrive/commit/acf80cd0849ffca79190c2dddb06cdcf0aef91fb) adds backward-compatible portable experiment metadata, fixes stale training-run association, and tests renamed transfer/malformed fields. [c44aa68](https://github.com/henrywork059/PiDrive/commit/c44aa6814cb96004ef04fdcd303d10869345c87f) wires matching manifest upload and loaded model context in PiSD/PiServer, retains existing server-side model checks. SHA-256 checks model bytes, not authenticity of run claims; absent/unavailable history stays Unknown.
- [6efc6d7](https://github.com/henrywork059/PiDrive/commit/6efc6d78a6171c24873e25356646f8cb4db2562f) adds visible optional same-frame AI comparison (existing default retained), named controls, native Qt sort/filter/toggle and cancelled bulk mutation assertions, contextual playback/purge help. Exact [Linux 45555355194](https://github.com/henrywork059/PiDrive/actions/runs/45555355194) PiSD/PiServer/manifest jobs passed; piTrainer cancelled by successor. [Windows 45555355189](https://github.com/henrywork059/PiDrive/actions/runs/45555355189) passed.
- [16eca3a](https://github.com/henrywork059/PiDrive/commit/16eca3a660219af82deb06b612fd597978a54e3c) adds PiSD front-workspace rejected STOP feedback, keyboard diagnostic details and bounded event GET including body, four added Chromium cases with intercepted mutations and simulated clipboard. [174026c](https://github.com/henrywork059/PiDrive/commit/174026cf1ca0919cd79ec4656867b9c21816f943) adds genuine CPU TensorFlow conversion/interpreter output-order test in the clean full dependency environment, without training or physical actuation.
- Current candidate 174026cf1ca0919cd79ec4656867b9c21816f943: PiSD 0.11.33, PiServer 0.4.41, piTrainer 0.11.21. Exact candidate CI: Hardware-free regression gate: [45555698348](https://github.com/henrywork059/PiDrive/actions/runs/45555698348) completed/success (4/4); Windows native Qt acceptance checks: [45555698560](https://github.com/henrywork059/PiDrive/actions/runs/45555698560) completed/success (1/1). Six forward commits since 821def6, 33 changed/new files, no deletions or inactive component changes. No new user configuration writes or runtime merge/deployment. No full proposal closure until exact combined evidence and applicable acceptance gates; original counts remain 35/56, 21 outstanding, 3/9 batches completed. Batch 5 provenance and conversion, Batch 6 comparison and Batch 7 front diagnostics advanced; remaining broader accessibility/visual review, recording/calibration interactions, trainer artifact/readiness context, further modularization, and operator workspace acceptance still open. No physical Pi, real training or owner golden approval claimed.


## 2026-11-25 — exact verification and R35 follow-up

- [174026c](https://github.com/henrywork059/PiDrive/commit/174026cf1ca0919cd79ec4656867b9c21816f943) verified completed successfully: [Linux 45555698348](https://github.com/henrywork059/PiDrive/actions/runs/45555698348) 4/4 and [Windows 45555698560](https://github.com/henrywork059/PiDrive/actions/runs/45555698560) 1/1. This supersedes b641f02 as the last fully verified candidate: PiSD 0.11.33, PiServer 0.4.41, piTrainer 0.11.21. Real TensorFlow-to-TFLite conversion/interpreter output-order test passed in the Linux full-dependency gate. Native Windows Qt checks passed; owner visuals, real training and physical deployment remain separate.
- [e878c0d](https://github.com/henrywork059/PiDrive/commit/e878c0d8da3476a3887188e4c4c18cb9af7d67d0) advances PiServer to 0.4.42 under R35 (Batch 4): eight visual-only style preview controls are inert, the dialog focus trap excludes inert controls, and the existing native Chromium four-width suite traverses real Tab order through actual settings and Save. The JavaScript R35 suite retains existing assertions and adds two checks. Exact new candidate CI pending; 174026c remains the verified baseline until both gates pass. One forward commit, seven files changed/new, no inactive component or config changes. No runtime merge or stable promotion. Counts unchanged: **35/56 (62.5%), 21 partial, 3/9 batches complete**.
