# PiDrive — Engineering and UI/UX Roadmaps

These four planning documents contain **75 numbered proposals**, grouped by engineering correctness, additional improvements, refinements, and UI/UX. They are **recommendations**, not implemented patches or a claim that the current GitHub checkout has been retested.

## Active implementation scope — 2026-11-24

Active development: PiSD, PiServer and piTrainer only. PiBooter, CustomTrainer and CustomDrive are inactive historical components; do not create, reopen, merge or continue their component-specific updates unless explicitly requested. Preserve existing source and history. Shared active-runtime safety and model-family rejection checks remain in scope.

The original proposal IDs are retained for historical traceability. Ignore inactive-component-only tasks; for mixed proposals, implement only the active component portions. The 13 inactive-component drafts (#43, #47, #51, #57, #58, #60, #62, #65, #68, #70, #74, #77, #80) were closed unmerged; five PiBooter drafts (#44, #48, #52, #71, #79) are also retired unmerged. Earlier merged history is unchanged. Consult [stabilization acceptance](../stabilization_acceptance.md) and the live GitHub PR list for active versions and test results. A draft or merged patch is not evidence of physical hardware validation.

## Progress tracking

See [active roadmap progress](PROGRESS.md) for the scoped proposal count, partial items and remaining work. Original IDs are not renumbered. The [consolidated development schedule](DEVELOPMENT_SCHEDULE.md) is complete: 56/56 active proposals and 9/9 batches in verified software scope. See [approved web screenshot baseline](../ui_baseline_review.md) and [final release-candidate handover](RELEASE_CANDIDATE_HANDOVER.md). Separate release acceptance remains open; no stable promotion or deployment.

## Roadmap documents

| Track | IDs | Document | Focus |
| --- | --- | --- | --- |
| Foundational engineering | F1–F10 | [Code review and update roadmap](PiDrive_Code_Review_and_Update_Roadmap.md) | Control safety, configuration, access, validation, maintainability |
| Expanded engineering | U11–U29 | [Expanded update roadmap](PiDrive_Expanded_Update_Roadmap.md) | Data integrity, model compatibility, runtime ownership, AI reliability |
| Refinement | R30–R53 | [Refinement roadmap](PiDrive_Refinement_Roadmap.md) | Workflow, diagnostics, responsiveness, performance, maintainability |
| UI/UX | UX54–UX75 | [UI/UX improvement plan](PiDrive_UI_UX_Improvement_Plan.md) | Usability, interface hierarchy, training workflow, accessibility |

## Follow-on improvement tracks (proposed)

- [UI/UX Improvement 2 — workflow and design-system roadmap](PiDrive_UI_UX_Improvement_2_Plan.md): reference-led improvements for PiSD, PiServer and piTrainer, with conditional PiSD Emulator test integration. New UI2-01–UI2-15 proposals; do not change the completed historical 56/56 and 9/9 accounting or approved web baseline. Planning only; reconcile concurrent performance/emulator branches before implementation.

- [Visual Design Update 1 — owner-approved design direction](PiDrive_Visual_Design_Update_1_Plan.md): ten approved decisions, VD01–VD36 (0/36 implementation), 11 milestones, six batches; PiSD, PiServer, piTrainer and conditional PiSD Emulator presentation. Planning only; preserve 56/56 and 9/9 historical accounting, UI2 and performance contracts, pinned visual baseline and versions. Reconcile #98/#99 integration/release and #100 settings-flood plan before overlapping implementation.

## Suggested execution order

1. **Safety and integrity:** implement the identified motor-control fail-safes, input validation, AI verification repairs, and train/validation split safeguards before cosmetic updates.
2. **Integration and reliability:** address model compatibility, ownership of Pi hardware, recording recovery, and configuration resilience.
3. **Workflow and usability:** improve trainer data review, operational status visibility and diagnostic feedback.
4. **Performance and long-term maintenance:** benchmark caching/polling, modularize high-complexity files where justified, and add CI/UI regression checks.

Within a phase, prioritize by **risk, reproducibility, dependencies, and testability**, rather than proposal number alone.

## Baseline and implementation safeguards

- These plans were prepared **2026-11-21/22**, primarily from `PiDrive-main.zip`, plus newer `PiSD_0_11_0.zip` and `piTrainer_0_11_0.zip`. A finding is not proof that an issue still exists in a later GitHub checkout.
- Before implementing an item, inspect the **live code** and the component's **latest and previous three patch notes**. Confirm entry points, active version, and dependency chains.
- Preserve user-local configuration and previously accepted UI/runtime behavior. Do **not** restore older PiSD or piTrainer source from the monorepo archive over the newer accepted component baselines.
- Keep component-specific work in its own component; use established patch-only packaging and `PATCH_NOTES/` conventions for actual code changes.
- Add tests for the acceptance criteria in each proposal. State separately what was tested locally and what still requires physical Raspberry Pi, Windows GUI, or training-environment verification.
- Avoid creating release tags or incrementing version lines for roadmap documentation alone.

**Planning status:** No application/runtime source changes are part of adding these documents.


## Main integration reconciliation — 2026-11-27

The owner explicitly requested merging all open PiDrive PRs into main. All 24 open PR heads (#45, #46, #49, #50, #53, #54, #55, #56, #59, #61, #63, #64, #66, #67, #69, #72, #73, #75, #76, #78, #82, #83, #86, #87) were individually verified as ancestors of, or equal to, the exact green completed candidate 6aaee7050485a6b1c3f841cd5837db8be4820768. Linux [45960538086](https://github.com/henrywork059/PiDrive/actions/runs/45960538086) 4/4 and Windows [45960538133](https://github.com/henrywork059/PiDrive/actions/runs/45960538133) 1/1 passed. No independent replay of older patches is required.

Previous main 8dfae027ae200757f6adf7669ea8a9b84b8db884 and the completed candidate diverged from c615c73032d62daa23ec0fe302d1cfe6049428c3. Complete recursive Git blob inventories showed no main-only file changes, two identically changed files and five differing documentation paths; 322 candidate-only changed paths. Retain the final candidate's software, version markers, tests, and 56/56 / 9/9 accounting; preserve all previous main commits as the second parent of this reconciliation. Historical main documents remain accessible at the immutable [progress snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/PROGRESS.md), [schedule snapshot](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/DEVELOPMENT_SCHEDULE.md), [README](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/README.md), [roadmap index](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/roadmaps/README.md) and [acceptance record](https://github.com/henrywork059/PiDrive/blob/8dfae027ae200757f6adf7669ea8a9b84b8db884/docs/stabilization_acceptance.md). Older progress counts are superseded, not deleted from history.

The candidate-first merge-parent order preserves the version-changing first-parent history used by tools/check_forward_packages.py. Integrate by a normal non-forced fast-forward of main to the reconciliation commit, only while both source references remain as verified. No production source, configuration, regression, version marker, retired component, or approved visual baseline changes in this reconciliation. Merge authorization does not imply stable promotion, hardware deployment, native desktop visual or assistive-technology approval. No release tag or new version. Verify final main and its CI separately.
