# Development milestone and handover template

Copy this template into a new component patch note, PR description or development log entry as appropriate. Do not overwrite this template or historical notes. Fill unknown fields with NOT VERIFIED / NOT RUN rather than guessing. Keep a source-backed handover short enough for another developer or coding agent to use immediately.

## 1. Task and authorization

- Date / owner request:
- Workstream and requirement IDs:
- Requested outcome and completion criteria:
- Authorized scope (components, branch, merge, stable, deployment — separately):
- Explicit exclusions / inactive components:

## 2. Starting state

| Item | Exact value |
| --- | --- |
| Live main SHA | |
| Working branch and HEAD | |
| Base/parent SHA | |
| Related PRs and their HEADs | |
| Current and proposed component versions | |
| Latest four patch notes reviewed | |
| Immutable benchmark/visual baselines (if relevant) | |
| Last exact fully qualified source and CI | |

## 3. Changes and regressions

| Requirement | Changed paths and behavior | Status (complete/partial/blocked) | Evidence |
| --- | --- | --- | --- |
| | | | |

| Issue | Observed symptom and cause/hypothesis | Failing run/test | Corrective commit | Passing evidence or remaining blocker |
| --- | --- | --- | --- | --- |
| | | | | |

For each change, specify what previous behavior must be preserved and what was actually verified. Include migration or config safety effects. Avoid a file-count-only summary.

## 4. Verification record

| Gate | Exact source SHA / run link / command | Outcome | Evidence or limit |
| --- | --- | --- | --- |
| Relevant deterministic tests | | NOT RUN | |
| Linux component and manifest/package gate | | NOT RUN | |
| Windows/native Qt | | NOT RUN | |
| Browser/emulator | | NOT RUN | |
| Visual artifact review (requested vs realized geometry, hashes, fonts) | | NOT RUN | |
| Performance paired measurements and parity | | NOT RUN | |
| Forward package dry run | | NOT RUN | |
| Physical P0 | | NOT RUN | |
| Owner visual/functional acceptance | | NOT VERIFIED | |

Use only applicable gates; justify N/A. Include actual run attempt, failed job ID, artifact ID and hash when available. Mark cancelled/skipped/missing separately. A prior green SHA does not qualify newer code. Do not claim independently inspected artifacts unless bytes were actually inspected.

## 5. Anti-rollback and status

- Prior accepted fixes/layout/settings/data/security preserved:
- Concurrent branches reconciled:
- Historical patch notes and baseline identity retained:
- Current candidate and latest fully qualified SHA:
- Exact CI pending/failed and first corrective task:
- Merge status / owner acceptance / stable / deployment (distinct):
- Known limitations, untested hardware/OS/workflows:
- Next substantial milestone, ordered by dependency and risk:

## 6. Copy-ready next task

Continue PiDrive [workstream] from exact HEAD [SHA] on [branch/PR]. Verify live main and related concurrent branches; verify exact [CI run IDs] and resolve real failures first. Prioritize [functional requirement IDs and observable completion criteria]. Preserve [specific previous fixes, safety, configuration, data, UI and benchmark contracts]. Add focused regressions and independently inspect applicable artifacts. Publish candidate [version only if justified and available]. Follow [AGENTS.md](../../AGENTS.md), [integration playbook](INTEGRATION.md) and [stabilization gate](../stabilization_acceptance.md). Do not merge, promote or deploy without separate authorization.
