# Consolidated active development schedule — 2026-11-24

This is the current execution plan, replacing one-proposal-at-a-time scheduling. It retains every outstanding original active proposal and all earlier accepted improvements. The original four roadmap documents remain historical requirements; their IDs are not renumbered.

## Scope and accounting

- Active: PiSD, PiServer, piTrainer. No new PiBooter/CustomTrainer/CustomDrive or legacy piCar work.
- Original proposals: 75; retired exclusive proposals: 19; active: 56.
- As of the current [progress audit](PROGRESS.md): 29 implemented, 5 partial, 22 without a dedicated update. **27 original proposal IDs remain** in **9 development batches** (30 originally scheduled). The former PiBooter batch is removed; R48 remains implemented for the active runtimes.
- Batch numbers are planning units, not component versions, PR numbers, or calendar deadlines. Deliver related work together where safe, using separate component-owned commits, patch notes and patch-only archives when requested. No monolithic cross-component source rewrite.
- Sequence is dependency- and acceptance-gated, not an invented time estimate. Independent work may proceed once its stated prerequisites are met; no unsafe parallel release or merging without authorization.

## Current starting point

[PR #86](https://github.com/henrywork059/PiDrive/pull/86) is the green active integration baseline ([CI 45354927996](https://github.com/henrywork059/PiDrive/actions/runs/45354927996)). [PR #87](https://github.com/henrywork059/PiDrive/pull/87) adds F4 validation and STOP fixes, U21 PiServer camera safety, and F2 PiSD manual-command watchdog in separate commits. The latest [CI run 45356933493](https://github.com/henrywork059/PiDrive/actions/runs/45356933493) passed all four jobs. Candidate versions: PiSD 0.11.24, PiServer 0.4.29, piTrainer 0.11.10. F3 is the remaining Batch 1 implementation. Neither candidate is merged or physically validated. See [PROGRESS.md](PROGRESS.md) for individual evidence and limits.

## Batch sequence

| Batch | Priority | Focus | Original IDs | Remaining | Prerequisites |
| --- | --- | --- | --- | ---: | --- |
| 1 | P0 | Runtime safety and validation | F2, F3, F4, U21 | 1 | Green PR #86 baseline |
| 2 | P1 | Configuration and data protection | F7, UX74 | 2 | 1 |
| 3 | P1 | Release automation and anti-rollback | F9, R53 | 2 | 1–2 |
| 4 | P1 | UI regression and accessibility foundation | R35, R36, R45, R50, UX75 | 5 | 1–3 |
| 5 | P1 | Training and deployment integration | F10, R51, UX62, UX64 | 4 | 1–4 |
| 6 | P1 | piTrainer data-review workflow | UX61, UX63, UX65 | 3 | 4, 5 |
| 7 | P1/P2 | PiSD driving interface | R49, UX54, UX55, UX56, UX57 | 5 | 1, 2, 4 |
| 8 | P2 | Code modularization | F8, R52 | 2 | 1–4; rerun tests from completed batches |
| 9 | P1/P2 | PiServer operator workspace | UX58, UX59, UX60 | 3 | 4, 8 |
| Total | | | | 27 | |

### Batch 1 — Runtime safety and validation

**Components:** PiSD, PiServer. **Status:** In progress (F2, F4, U21 passed scoped automated gates; F3 outstanding).

**Scope:** Finish the two PiSD standalone validation commands (F4); implement and test PiSD's server-side manual command lease/watchdog (F2); add PiSD LAN authorization/access protection with authorized STOP and explicit compatibility guidance (F3); audit and complete PiServer stale-camera autonomous-motion stop/rearm (U21). Separate each safety concern into a reviewable commit/subpatch.

**Acceptance gate:** Both full simulation validation commands pass; fake-clock timeout/dropout and authorized/unauthorized control tests; stale-frame and explicit rearm tests; no STOP regression. Supervised Pi hardware safety acceptance remains a separate release gate.

### Batch 2 — Configuration and data protection

**Components:** All active components, where applicable. **Status:** Planned.

**Scope:** Complete corrupt-config preservation and recovery warnings in affected active runtimes; retain recovery copies, safe normalization and round trips. Pair with clear destructive-action confirmations, exact targets, duplicate-submit protection and truthful undo availability in each applicable interface. Never confirmation-gate emergency STOP.

**Acceptance gate:** Malformed-file and restart tests, original bytes preserved, exact deletion targets, no accidental data/config overwrites, no STOP delay.

### Batch 3 — Release automation and anti-rollback

**Components:** Monorepo / three active components. **Status:** Planned.

**Scope:** Align dependency groups and launch instructions; add changed-file-only package manifests, base identifiers, hashes, allowed paths, cache/user-data exclusions and dry-run validation against accepted baseline and latest plus three preceding notes. Do not move components or modify persistent user settings.

**Acceptance gate:** Clean dependency smoke checks; package validation accepts intended patch and rejects stale/wrong-component/extra-file packages; notes report actual tests.

### Batch 4 — UI regression and accessibility foundation

**Components:** All active interfaces. **Status:** Planned.

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
