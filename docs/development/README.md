# PiDrive developer handbook

Purpose: practical reference for maintainers and AI coding agents. This guide supplements [AGENTS.md](../../AGENTS.md); it does not override owner instructions, roadmap acceptance, or component version rules. Source inventory verified against main 8f593778eb461f8515f6c12c5fce936dc64cb301 on 2026-11-28. Live branches, version markers and exact CI take precedence over this dated snapshot.

## Start here

| Task | Read |
| --- | --- |
| Understand a component or find the implementation | [Architecture and code map](ARCHITECTURE.md) |
| Change an API, recorder, model or trainer data path | [Interface and data contracts](CONTRACTS.md) |
| Choose tests or interpret a CI result | [Testing and CI playbook](TESTING.md) |
| Diagnose an error or a regression | [Debugging runbook](DEBUGGING.md) |
| Reconcile parallel branches, package or release | [Integration and release playbook](INTEGRATION.md) |
| Start/finish a milestone or hand over work | [Development handover template](HANDOVER.md) |

## First 15 minutes of a task

1. Identify the owner-requested outcome, scope and acceptance gate. Read AGENTS.md.
2. Fetch live main and the intended workstream HEAD. Check open PRs for overlapping source, version numbers and CI.
3. Read the actual launcher/service/UI path, latest component note and preceding three notes. Do not use an old ZIP to overwrite newer accepted code.
4. Reproduce or identify a concrete failing assertion. Agree on observable completion evidence before making changes.
5. Implement a forward, scoped change with regression tests. Inspect the diff, run relevant tests, qualify the exact SHA, document evidence and limits.

## Authoritative existing records

- [Original roadmap and plans](../roadmaps/README.md) — historical proposal IDs and acceptance.
- [Development and error log](../roadmaps/DEVELOPMENT_AND_ERROR_LOG.md) — chronological outcomes, corrections, CI and preventive lessons.
- [Performance roadmap](../roadmaps/PiDrive_Performance_Optimization_Plan.md) and [UI2 plan](../roadmaps/PiDrive_UI_UX_Improvement_2_Plan.md).
- [Release candidate handover](../roadmaps/RELEASE_CANDIDATE_HANDOVER.md), [stabilization acceptance](../stabilization_acceptance.md), [approved UI reference](../ui_baseline_review.md), [UI regression gate](../ui_regression_gate.md).
- [Dependency groups](../dependency_groups.md), [patch packaging](../patch_package.md), [bug prevention](../../BUG_PREVENTION_NOTES.md).

Keep completed implementation, automated qualification, merge, owner acceptance, stable promotion and deployment as separate states. Historical roadmap completion does not close new workstreams. Preserve active component boundaries; PiBooter, CustomTrainer and CustomDrive remain inactive unless explicitly reactivated. PiSD Emulator is a local development/test companion, not a substitute for real hardware.

Maintenance: when a verified architectural or contract change occurs, update only the corresponding reference and add an entry to the component patch notes/development log. Do not put fast-changing CI snapshots into every guide.
