# PiDrive — Engineering and UI/UX Roadmaps

These four planning documents contain **75 numbered proposals**, grouped by engineering correctness, additional improvements, refinements, and UI/UX. They are **recommendations**, not implemented patches or a claim that the current GitHub checkout has been retested.

## Active implementation scope — 2026-11-24

Active development: PiSD, PiServer, piTrainer and PiBooter only. CustomTrainer and CustomDrive are inactive historical components; do not create, reopen, merge or continue their component-specific updates unless explicitly requested. Preserve existing source and history. Shared active-runtime safety and model-family rejection checks remain in scope.

The original proposal IDs are retained for historical traceability. Ignore inactive-component-only tasks; for mixed proposals, implement only the active component portions. The 13 inactive-component drafts (#43, #47, #51, #57, #58, #60, #62, #65, #68, #70, #74, #77, #80) were closed unmerged; earlier merged history is unchanged. Consult [stabilization acceptance](../stabilization_acceptance.md) and the live GitHub PR list for active versions and test results. A draft or merged patch is not evidence of physical hardware validation.

## Progress tracking

See [active roadmap progress](PROGRESS.md) for the scoped proposal count, partial items and remaining work. Original IDs are not renumbered.

## Roadmap documents

| Track | IDs | Document | Focus |
| --- | --- | --- | --- |
| Foundational engineering | F1–F10 | [Code review and update roadmap](PiDrive_Code_Review_and_Update_Roadmap.md) | Control safety, configuration, access, validation, maintainability |
| Expanded engineering | U11–U29 | [Expanded update roadmap](PiDrive_Expanded_Update_Roadmap.md) | Data integrity, model compatibility, runtime ownership, AI reliability |
| Refinement | R30–R53 | [Refinement roadmap](PiDrive_Refinement_Roadmap.md) | Workflow, diagnostics, responsiveness, performance, maintainability |
| UI/UX | UX54–UX75 | [UI/UX improvement plan](PiDrive_UI_UX_Improvement_Plan.md) | Usability, interface hierarchy, training workflow, accessibility |

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
