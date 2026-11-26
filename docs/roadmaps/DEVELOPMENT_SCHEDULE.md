# Consolidated active development schedule — updated 2026-11-27

This is the current execution plan, replacing one-proposal-at-a-time scheduling. It retains every outstanding original active proposal and all earlier accepted improvements. The original four roadmap documents remain historical requirements; their IDs are not renumbered.

## Scope and accounting

- Active: PiSD, PiServer, piTrainer. No new PiBooter/CustomTrainer/CustomDrive or legacy piCar work.
- Original proposals: 75; retired exclusive proposals: 19; active: 56.
- Current verified software baseline: **42/56 implemented, 14 remaining, 4/9 batches complete**. See [progress audit](PROGRESS.md) for per-ID accounting and candidate evidence. All remaining requirements and batches are authorized, including Batch 6 onward. Original batch mapping below is retained for traceability; the 30 IDs are the historical schedule scope, not the current remaining count.
- Batch numbers are planning units, not component versions, PR numbers, or calendar deadlines. Deliver related work together where safe, using separate component-owned commits, patch notes and patch-only archives when requested. No monolithic cross-component source rewrite.
- Sequence is dependency- and acceptance-gated, not an invented time estimate. Independent work may proceed once its stated prerequisites are met; no unsafe parallel release or merging without authorization.

## Historical starting point (2026-11-24; superseded)

Former PR #84 (PiSD 0.11.22, PiServer 0.4.28, piTrainer 0.11.10, then also PiBooter 0.1.8) passed all five jobs in [45349043534](https://github.com/henrywork059/PiDrive/actions/runs/45349043534). It is superseded by the clean three-component candidate and is not physically accepted. The F4 follow-up from PR #85 starts Batch 1. [45353829480](https://github.com/henrywork059/PiDrive/actions/runs/45353829480) passed the four new production-math cases and existing selected PiSD regressions, but the standalone validation step failed: standard validation 59 passed / 4 failed (AI source tokens, settings page marker, testing GUI manifest contract, control STOP assertion). Do not count F4 complete or bypass those checks. Other four jobs passed. No new runtime fixes are made by this scope update.

## Batch sequence

Current baseline mapping: 1, 2, 3, 5 complete; 4, 6, 7, 8, 9 remaining. Dependency-aware cross-batch implementation is authorized; acceptance gates remain mandatory. The six previous STOP failures passed at exact green 2a36fe3; preserve these gates throughout later-batch implementation.

| Batch | Priority | Focus | Original IDs | Count | Prerequisites |
| --- | --- | --- | --- | ---: | --- |
| 1 | P0 | Runtime safety and validation | F2, F3, F4, U21 | 4 | Green PR #84 baseline |
| 2 | P1 | Configuration and data protection | F7, UX74 | 2 | 1 |
| 3 | P1 | Release automation and anti-rollback | F9, R53 | 2 | 1–2 |
| 4 | P1 | UI regression and accessibility foundation | R35, R36, R45, R50, UX75 | 5 | 1–3 |
| 5 | P1 | Training and deployment integration | F10, R51, UX62, UX64 | 4 | 1–4 |
| 6 | P1 | piTrainer data-review workflow | UX61, UX63, UX65 | 3 | 4, 5 |
| 7 | P1/P2 | PiSD driving interface | R49, UX54, UX55, UX56, UX57 | 5 | 1, 2, 4 |
| 8 | P2 | Code modularization | F8, R52 | 2 | 1–4; rerun tests from completed batches |
| 9 | P1/P2 | PiServer operator workspace | UX58, UX59, UX60 | 3 | 4, 8 |
| Total | | | | 30 | |

### Batch 1 — Runtime safety and validation

**Components:** PiSD, PiServer. **Status:** Complete in supplied baseline accounting.

**Scope:** Finish the two PiSD standalone validation commands (F4); implement and test PiSD's server-side manual command lease/watchdog (F2); add PiSD LAN authorization/access protection with authorized STOP and explicit compatibility guidance (F3); audit and complete PiServer stale-camera autonomous-motion stop/rearm (U21). Separate each safety concern into a reviewable commit/subpatch.

**Acceptance gate:** Both full simulation validation commands pass; fake-clock timeout/dropout and authorized/unauthorized control tests; stale-frame and explicit rearm tests; no STOP regression. Supervised Pi hardware safety acceptance remains a separate release gate.

### Batch 2 — Configuration and data protection

**Components:** All active components, where applicable. **Status:** Complete in supplied baseline accounting.

**Scope:** Complete corrupt-config preservation and recovery warnings in affected active runtimes; retain recovery copies, safe normalization and round trips. Pair with clear destructive-action confirmations, exact targets, duplicate-submit protection and truthful undo availability in each applicable interface. Never confirmation-gate emergency STOP.

**Acceptance gate:** Malformed-file and restart tests, original bytes preserved, exact deletion targets, no accidental data/config overwrites, no STOP delay.

### Batch 3 — Release automation and anti-rollback

**Components:** Monorepo / three active components. **Status:** Complete in supplied baseline accounting.

**Scope:** Align dependency groups and launch instructions; add changed-file-only package manifests, base identifiers, hashes, allowed paths, cache/user-data exclusions and dry-run validation against accepted baseline and latest plus three preceding notes. Do not move components or modify persistent user settings.

**Acceptance gate:** Clean dependency smoke checks; package validation accepts intended patch and rejects stale/wrong-component/extra-file packages; notes report actual tests.

### Batch 4 — UI regression and accessibility foundation

**Components:** All active interfaces. **Status:** In progress; R45 counted in baseline and R36 verified; R35/R50/UX75 remain open.

**Scope:** Finish desktop accessibility audit and PiSD token/drift coverage; add native Qt and browser interaction/geometry smoke tests covering keyboard, touch, focus, no-data, failures and 390/768/1024/1440 widths. Record accepted baseline captures before visual changes. Use this suite for subsequent UI batches.

**Acceptance gate:** Existing layout and controls preserved; STOP and Save reachable; stable frame selection, splitter/focus behavior; baseline images reviewed separately from automated checks.

### Batch 5 — Training and deployment integration

**Components:** PiSD, piTrainer, PiServer. **Status:** Complete in supplied baseline accounting.

**Scope:** Synthetic current/legacy recording fixtures, label edit/hidden/flip/export contracts; link recording, preprocess, training, validation, export and loaded model provenance without invented historical fields; add compact tab readiness markers and readable plot/run/artifact context.

**Acceptance gate:** Deterministic recording-to-model contract tests, preserved model family/checksum checks, missing-link handling, no overwritten artifacts or altered six-tab order. Actual training/deployment acceptance separate.

### Batch 6 — piTrainer data-review workflow

**Components:** piTrainer. **Status:** In progress; UX61/UX63/UX65 implemented or retained, Linux trainer and expanded Windows suite passed; combined acceptance pending.

**Scope:** Contextual bulk-edit preview with exact count and representative old/new values; synchronized label/prediction comparison keyed to stable source-frame identity; contextual keyboard help without intercepting text entry. Preserve all 0.11.10 selection fixes and existing edit/hide/delete shortcuts.

**Acceptance gate:** Native Qt tests for sort/filter/selection/validation return, exact mutation scope, compare identity, playback and shortcut behavior.

### Batch 7 — PiSD driving interface

**Components:** PiSD. **Status:** In progress; R49/UX54 verified, UX55/UX56/UX57 revised, PiSD Linux passed; exact candidate acceptance pending.

**Scope:** Finish sanitized bounded recent operator events; task-first front page; preview-first hierarchy with status and STOP reachable; recording mini-toolbar using confirmed counters/outcomes; geometry/appearance calibration grouping with scoped reset.

**Acceptance gate:** No raw secrets in events, no automatic arming, no duplicate safety acknowledgement, unchanged overlay calibration/defaults and saved recording format; responsive smoke tests.

### Batch 8 — Code modularization

**Components:** Affected active modules, especially PiServer. **Status:** In progress; pure docking geometry extracted, broader parity acceptance pending.

**Scope:** Characterize behavior before extracting pure parsing, formatting, validation and controller/DOM helpers. Keep stable public APIs, config paths, component boundaries and launchers. Prefer small staged extractions rather than a rewrite.

**Acceptance gate:** Characterization and regression parity; no changed route or config semantics, no lost shortcuts/layout/previous fixes.

### Batch 9 — PiServer operator workspace

**Components:** PiServer. **Status:** In progress; UX58–UX60 revised, exact combined acceptance pending.

**Scope:** Tier status telemetry with essentials visible, distinguish hardware actions from layout and destructive actions, add non-destructive Driving/Camera tuning/Model testing presets with preview/cancel. Retain saved custom layout and theme.

**Acceptance gate:** Responsive and keyboard checks, existing motor/camera/STOP behavior, saved layout survives cancel/restart; only explicit save replaces user layout.

## Execution and reporting rules

1. Inspect the live branch and latest plus three prior component notes before editing; start from the latest accepted/integrated state. Do not overwrite with older ZIP contents.
2. Characterize any overlapping already-implemented functionality before changing it. Implement only the remaining active portions of each proposal.
3. Keep safety, authorization and hardware-control changes independently reviewable and testable even when scheduled as one batch. Preserve the previously green candidate until the replacement passes.
4. Run the affected component tests and full active regression gate. Record simulation/browser/Qt/Windows/physical hardware verification separately; do not weaken tests to obtain green status.
5. For each completed batch update PROGRESS.md with per-ID evidence, remaining original IDs, completed/remaining batches, actual component versions and CI links. A batch is complete only when every included active proposal meets its scoped implementation/verification gate; partial completion decreases the proposal count only as justified by evidence.
6. Keep release/merge authorization and physical acceptance separate. No calendar delivery dates or version numbers assigned before implementation.
