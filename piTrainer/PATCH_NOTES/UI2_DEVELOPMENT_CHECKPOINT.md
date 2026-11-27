# UI/UX Improvement 2 — unversioned trainer development checkpoint

Date: 2026-11-27. Draft PR #91, not a release candidate.

## Request and cause
UI2-03/09/14: improve task readiness and collect native desktop visual evidence. Existing MainWindow.refresh_workflow_readiness used icons and tooltips to convey Needs input / Inputs available / Done, without explicitly setting native tab accessibility names. The historical 105-image approval is web-only; no trainer native screenshot archive was approved.

## Changes
- piTrainer/piTrainer/main_window.py: mirror the existing readiness and truthful detail in each QTabBar accessible name, retaining the visible tab text, icon, tooltip, navigation order, action bindings and readiness calculation.
- tools/check_ui2_trainer.py: run actual MainWindow in a disposable local fixture, exercise six native tab navigation transitions, inspect empty / synthetic row / restored readiness, capture twelve widget PNGs per revision, write revision, dimensions and SHA-256 manifest.
- .github/workflows/ui2-trainer-visual.yml: exact pinned main and candidate worktrees on Linux and Windows, same desktop dependency ranges, separate capture artifacts. Offscreen Qt widget rendering is not physical screen-reader/native OS visual approval.

## Anti-rollback and verification
Inspected current main, latest four piTrainer notes 0.11.32/31/30/29 and actual launcher, window and shared widgets. Checked main_window.py blob matches pending Performance Update 2 at ba05d2acfa537acefd031dde3f1b79977f27652d before targeted replacement. No changes to runtime, user settings, model or data, shared performance code, tab topology or accepted visual baseline. Qt 6.8 documents setAccessibleTabName; design references Fluent 2 tabs/accessibility, WCAG 2.2 and Carbon status feedback. No new dependency. Local native Qt unavailable; exact CI and actual screenshot inspection remain pending. The new workflow is not evidence of a passed test until its exact revision completes and artifacts are inspected.

## Version and limits
No version assigned to this draft checkpoint: piTrainer 0.11.33/34 are already pending in Performance #88/#89; reconcile and requalify before packaging or allocating a new version. No stable promotion, merge, release tag, package or physical acceptance. This is a partial implementation, not completion of UI2-03/09/14.
