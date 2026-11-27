# PiDrive development and regression log — 2026-11-27/28

Snapshot: 2026-11-28, Taipei time. Repository state inspected directly through GitHub. This is a consolidated engineering record, not a release approval. Component PATCH_NOTES and immutable Git commits remain the detailed source of truth. Run conclusions below are point-in-time observations; recheck the exact current SHA before further integration.

## 1. Baselines and integration state

- Inspected main: [f5e58cf72d6b673870b9e368ebcd3458b2357d4c](https://github.com/henrywork059/PiDrive/commit/f5e58cf72d6b673870b9e368ebcd3458b2357d4c).
- Open integration [PR #98](https://github.com/henrywork059/PiDrive/pull/98), branch `integration/performance-ui2-main-20261128`, inspected HEAD `a4b9496b9c5d302b9a574e7e69984d8686b13b4f`. Do not treat a branch candidate as merged.
- Merged candidate lines: PiSD 0.11.48, PiServer 0.4.55, piTrainer 0.11.34 (latest component notes). Integration proposes PiSD 0.11.49, PiServer 0.4.56 and piTrainer 0.11.36, with intermediate trainer 0.11.35 retained.
- Historical accepted baseline lines remain PiSD 0.11.0, piTrainer 0.11.0, PiServer 0.4.0 unless separately superseded by the owner. No stable promotion, deployment or hardware approval follows from this log.
- Original performance comparison baseline: `14c57c990ff0f9bae2003e4e8aa552d17a4227c7`; preserve it across subsequent benchmark runs.
- Original scoped software roadmap: 56/56 proposals, 9/9 batches completed; 19 retired exclusive proposals remain retired. This does not count UI2 or Performance 2 as complete.

## 2. What we implemented

| Workstream | Git record | Delivered / scope |
| --- | --- | --- |
| Original roadmap | [#87](https://github.com/henrywork059/PiDrive/pull/87), merged `a31cbff` | Manual lease/watchdog, STOP and rearm, access tokens, stale inference rejection, config recovery/unknown keys, guarded destructive actions, package manifests, dependency profiles, accessibility/responsive work, recording/model provenance and trainer workflow improvements. Historical software acceptance separate from hardware. |
| Performance 1 | [#88](https://github.com/henrywork059/PiDrive/pull/88), merged `a115826` | Owned float32 in-place normalization; fewer unused placeholder and DOM operations; faster trainer row extraction, deterministic review ordering and parity checks. Owner authorized transition with two numerical misses, not full performance acceptance. |
| Performance 2 | [#89](https://github.com/henrywork059/PiDrive/pull/89), merged `77b3fe8` | Positional filtering, bounded JSONL ingestion, narrower training metadata, optional native lores YUV420 preview with stride validation/fallback, bounded JPEG delivery, real TFLite option qualification, reversible standard/economy preview profiles and mock resource soaks. Individual roadmap criteria remain partial; standard defaults and main capture/AI/recording contracts retained. |
| PiSD Emulator | [#90](https://github.com/henrywork059/PiDrive/pull/90), merged `b57f02c` | Deterministic virtual vehicle, first-person road stream, actual PiSD Manual Drive interface, injected virtual motor/camera adapters, isolated models/config/recordings and synthetic-source manifest. Initial 0.11.46 reconciled to 0.11.47 after performance merge. |
| UI2 plan | [#91](https://github.com/henrywork059/PiDrive/pull/91), merged `0ab971d` | 15 proposed requirements and five milestone gates; plan only. |
| Performance 2.5/2.6 development | [#93](https://github.com/henrywork059/PiDrive/pull/93), qualified `0f28889459796c6672b0b830c095205c83579e11` | Four-column plot projection, one owning review copy, bounded offline validation image preparation, column-oriented ingestion with global inference, explicit opt-in bounded deterministic training input; stochastic scheduling/defaults preserved. Full review RSS target and physical qualification not automatically met. |
| UI2 operator | [#94](https://github.com/henrywork059/PiDrive/pull/94), `1b32f1c42232b1082a9a9de01c1c2203829cc239` | Truthful virtual/hardware/fallback/unverified runtime, stale telemetry invalidation, avoid redundant DOM writes, compact workflow navigation; preserve STOP, access control and docking. |
| UI2 trainer | [#92](https://github.com/henrywork059/PiDrive/pull/92), [#95](https://github.com/henrywork059/PiDrive/pull/95), [#97](https://github.com/henrywork059/PiDrive/pull/97) | Accessible tab names, persistent active-stage readiness, visible prerequisites and navigation, actual Qt screenshot harness with platform/font checks. #97 replaces the older #95 package ancestry without replaying stale notes. |
| Emulator frame/security repair | [#96](https://github.com/henrywork059/PiDrive/pull/96), merged `f5e58cf` | Exact launcher-selected loopback frame-ancestors permission for emulator only; normal/physical DENY retained; protected controller mutations, runtime generation, restart/reload and live browser regressions. |
| Consolidation | [#98](https://github.com/henrywork059/PiDrive/pull/98), open | First-parent `9156909` integrates qualified 0.11.35 performance source; `e2f5221` integrates UI2 with 0.11.49/0.4.56/0.11.36, retains emulator security; `a4b9496` corrects integration accessibility regression. Exact combined gate still required. |

Merge order on 27 November (UTC): #91 15:45:24, #88 15:45:35, #89 15:45:49, #90 15:47:54, #96 16:12:18. Earlier draft status text in historical notes is not the current merge state.

## 3. Error register and preventive controls

### E01 — Trainer column materialization loses legacy schema parity

- Failed [Linux 46030742183](https://github.com/henrywork059/PiDrive/actions/runs/46030742183), HEAD `7151a8a2919430dd3281cc2a838d254a581c4cfe`, job [140613585384](https://github.com/henrywork059/PiDrive/actions/runs/46030742183/job/140613585384). Direct job logs inspected: `tests/test_record_streaming_p2.py::test_column_materialization_preserves_global_inference` failed at batch sizes 1, 7, 512 with DataFrame.columns mismatch; file result 3 failed/10 passed. Other three component/package jobs succeeded. The missing thread-report artifact is a separate downstream failure symptom, not evidence of thread-performance regression.
- Cause/repair: empty-schema DataFrame column index semantics differed from legacy pandas construction. [0f288894](https://github.com/henrywork059/PiDrive/commit/0f28889459796c6672b0b830c095205c83579e11) preserves the legacy empty object Index. Retain ordered columns, explicit None versus missing values, global dtype inference, labels/source identity and ordering across batch boundaries.
- Status: corrected on qualified performance source; exact Linux 46031258094 and Windows 46031258108 succeeded. Integrated candidate still needs combined CI.
- Prevention: test empty schema, mixed types, missing keys, global inference, source ordering and identical outputs at multiple batch sizes; never replace strict equality with permissive column reordering.

### E02 — Historical patch-note integrity / incorrect first-parent package baseline

- Failed [Linux 46032023140](https://github.com/henrywork059/PiDrive/actions/runs/46032023140), HEAD `e7a5cbb96947bad5497551c4fe4a5583ee7a1320`, job [140617935283](https://github.com/henrywork059/PiDrive/actions/runs/46032023140/job/140617935283). Direct log: `ValueError: Historical note changed: piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_35.md`. Three runtime/trainer jobs passed.
- Cause: #95 carried latest performance files on an older first-parent package baseline; the historical 0.11.35 note was different from that baseline. The guard correctly rejected it.
- Repair: #97 `bb87f1ca7a86c36d6bd11d0d453b4e310f509a2a` starts from the exact qualified performance parent, replays UI2 only and retains note bytes. Linux 46032802258, Windows 46032802236, visual 46032802353 all succeeded. Integration preserves the exact 0.11.35 tree at first-parent 9156909 before 0.11.36.
- Related earlier issue: package baseline off main first-parent chain after stacked merge (46028377559, recorded in trainer 0.11.35 note). Explicit inherited-source selection checks full ancestry and entire unchanged component-tree identity, then retains original baseline/version/history/hash/rollback checks; changed components still use their own forward baseline.
- Prevention: never rewrite historical notes, fabricate baseline ancestry, remove package checks or replay a superseded stacked PR independently.

### E03 — PiServer navigation targets lack computed accessible names

- Failed [Linux 46033174578](https://github.com/henrywork059/PiDrive/actions/runs/46033174578), HEAD `e2f5221f92916dec5a924d76efb1d11ca80297a6`, job [140621854682](https://github.com/henrywork059/PiDrive/actions/runs/46033174578/job/140621854682). Direct logs: native browser geometry/interaction and R36 responsive steps rejected focusable generic jump targets with missing_computed_name. R36 dashboard failed 390x844, 768x1024, 1024x768, 1440x900 and 844x390; other three jobs passed.
- Repair [a4b9496](https://github.com/henrywork059/PiDrive/commit/a4b9496b9c5d302b9a574e7e69984d8686b13b4f): in `PiServer/piserver/web/templates/index.html`, eight existing jump targets (viewer, runtime, model, manual, record, sessions, camera, motor) receive heading role, level 2 and visible-title accessible labels. IDs, tabindex, drive-key guard and layout stay intact. Patch and notes inspected.
- Status: fix committed, new combined Linux gate 46033851596 still running at inspection. Do not mark resolved before exact gate passes.
- Prevention: check real Chromium accessibility tree for every independently focusable target, including tabindex=-1 programmatic targets, across all required widths. Do not weaken inventory.

### E04 — PiSD emulator settings leakage risk and iframe denial

- Normal settings path regression repaired by `27d1a6db` with explicit workspace isolation regression `d8da59df`; emulator note `d59c12da`. Preserve ordinary settings paths when optional adapters are active, and never write simulation state to real hardware config.
- Owner observed working road camera and direct port 5050 access but blocked embedded real interface. Root cause: normal X-Frame-Options DENY. #96 repair `d9962539` / `6fdade8c` limits framing permission to exact selected loopback origin and retains DENY in normal/physical operation. Controller host/origin checks, runtime generation and browser interaction/STOP/alternate-port rejection regressions added.
- Status: merged main exact f5e58cf; Linux 46031594641 and emulator browser 46031594657 succeeded. No physical motor tests inferred.
- Prevention: exercise actual integrated iframe and controller, not merely separate URLs. Keep origin restrictions, authorization, STOP, generation handling and distinct workspaces intact.

### E05 — Windows screenshot evidence invalid despite green CI

- Prior #92 native Windows artifact 15213735418 contained missing-glyph boxes (documented independent review in trainer 0.11.36 note). Do not treat successful capture as readable visual evidence.
- Native Windows platform and glyph preflight correction produced readable Segoe UI in prior inspected artifacts 15214895480 / 15214905546; 48/48 manifest image hashes and dimensions matched according to component notes. Requested Windows 1024x768 and 1440x900 became 1024x749 and 1028x749. Wide Windows geometry still unqualified.
- #97 visual CI 46032802353 succeeded; combined visual run pending at inspection. Prior artifact findings cited from component notes, not new binary inspection in this documentation task.
- Prevention: record requested and realized viewport, Qt platform, font family, actual glyph rendering, image hash and baseline/candidate comparisons; distinguish native visual owner approval from automated pass.

### E06 — Performance shortfalls are not test failures or waivers of safety

- Owner-approved Performance 1 transition at 04c62e457060270a6f3398a703de0b9b393162fa: 5/7 numerical targets. PiSD idle CPU reduction 20.86% vs 25% target; concurrent 9.03% vs 10% target. PiServer idle/concurrent/inference reductions 36.37/29.17/53.70%; trainer p95 review 85.99% and peak RSS 11.70%. Source: merged performance plan's owner-transition entry and exact runs 46014075774, 46014075899, 46014075875, 46014075787.
- Trainer 25% whole-review RSS goal in later Performance 2 remains open per 0.11.35 note; isolated-operation gains cannot substitute for native process metrics. Real-device energy and sustained hardware workload still unqualified.
- Prevention: same immutable baseline, paired randomized repeated workloads, counts/freshness/output parity, CPU and RSS trade-offs, complete artifact reports, no selective substitution. No automatic new default or physical energy claim.

## 4. Exact CI ledger

| Source | Workflow run | Observed result |
| --- | --- | --- |
| Main f5e58cf | [46031594641](https://github.com/henrywork059/PiDrive/actions/runs/46031594641) Linux; [46031594657](https://github.com/henrywork059/PiDrive/actions/runs/46031594657) emulator | Both success |
| #93 0f288894 | [46031258094](https://github.com/henrywork059/PiDrive/actions/runs/46031258094) Linux; [46031258108](https://github.com/henrywork059/PiDrive/actions/runs/46031258108) Windows; [46031258088](https://github.com/henrywork059/PiDrive/actions/runs/46031258088) workload; [46031258455](https://github.com/henrywork059/PiDrive/actions/runs/46031258455) strict | All four success |
| #95 e7a5cbb | [46032023140](https://github.com/henrywork059/PiDrive/actions/runs/46032023140) Linux; 46032023170 Windows; 46032023012 visual | Linux failure E02; Windows/visual success |
| #97 bb87f1c | [46032802258](https://github.com/henrywork059/PiDrive/actions/runs/46032802258) Linux; [46032802236](https://github.com/henrywork059/PiDrive/actions/runs/46032802236) Windows; [46032802353](https://github.com/henrywork059/PiDrive/actions/runs/46032802353) visual | All success |
| #98 e2f5221 | [46033174578](https://github.com/henrywork059/PiDrive/actions/runs/46033174578) Linux; 46033174814 emulator; 46033174643 Windows; 46033174638 visual; 46033174593 strict; 46033174612 workload | Linux failure E03; emulator/Windows/visual success; strict/workload cancelled by successor |
| #98 a4b9496 | [46033851785](https://github.com/henrywork059/PiDrive/actions/runs/46033851785) emulator | Success |
| #98 a4b9496 | [46033851596](https://github.com/henrywork059/PiDrive/actions/runs/46033851596) Linux; [46033851618](https://github.com/henrywork059/PiDrive/actions/runs/46033851618) Windows; [46033851756](https://github.com/henrywork059/PiDrive/actions/runs/46033851756) visual; [46033851689](https://github.com/henrywork059/PiDrive/actions/runs/46033851689) strict; [46033851701](https://github.com/henrywork059/PiDrive/actions/runs/46033851701) workload | In progress at last inspection |

## 5. Next work / acceptance

1. Recheck live main and exact #98 HEAD; inspect actual results from all six combined workflows. Resolve only genuine failures, retain historical records and no weakened tests. Requalify whenever source changes.
2. Preserve #96 security and configuration isolation, exact #93 performance behavior and #97 trainer UI. Do not independently replay #92/#95 or allocate duplicate versions.
3. Independently review actual combined screenshot and resource artifacts; report realized geometry, populated trainer workflow, benchmark parity and all numerical shortfalls. Retain approved 105 web PNGs from ba2420536b733659c6cb4796490cdb38f8d31914 as immutable reference; new visual acceptance separate.
4. Keep merge authorization distinct from stable version promotion, physical STOP/rearm/watchdog/camera tests, installation and deployment. No hardware safety claim from virtual or fixture tests.
5. Keep this log additive: record date, exact source SHA, component versions, issue symptom/root cause, changed paths, failing and passing run links, evidence, limits and follow-up. Append corrections rather than erasing prior failures.

## 6. Existing detailed records

- [Original roadmap progress](PROGRESS.md) and [release-candidate handover](RELEASE_CANDIDATE_HANDOVER.md)
- [Performance plan and historical measurements](PiDrive_Performance_Optimization_Plan.md)
- [UI2 plan](PiDrive_UI_UX_Improvement_2_Plan.md); [integration UI2 progress at inspected HEAD](https://github.com/henrywork059/PiDrive/blob/a4b9496b9c5d302b9a574e7e69984d8686b13b4f/docs/roadmaps/UI2_PROGRESS.md)
- [Bug prevention notes](../../BUG_PREVENTION_NOTES.md), [stabilization acceptance](../stabilization_acceptance.md), [approved baseline](../ui_baseline_review.md)
- [PiSD 0.11.48 patch notes](../../PiSD/PATCH_NOTES/PATCH_NOTES_PiSD_0_11_48.md)
- [Trainer 0.11.35 qualified note](https://github.com/henrywork059/PiDrive/blob/0f28889459796c6672b0b830c095205c83579e11/piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_35.md)
- [Trainer 0.11.36 integration note](https://github.com/henrywork059/PiDrive/blob/a4b9496b9c5d302b9a574e7e69984d8686b13b4f/piTrainer/PATCH_NOTES/PATCH_NOTES_piTrainer_0_11_36.md)
- [PiServer 0.4.56 integration note](https://github.com/henrywork059/PiDrive/blob/a4b9496b9c5d302b9a574e7e69984d8686b13b4f/PiServer/PATCH_NOTES/PATCH_NOTES_PiServer_0_4_56.md)

Documentation verification: checked live main, PR metadata, commit history, exact workflow conclusions, three failing job logs, existing roadmap/acceptance and selected component patch notes, and accessibility correction diff. No new runtime execution, screenshot archive downloads, benchmark rerun, release packaging, physical hardware or owner acceptance was performed in this documentation task. This file does not modify code, settings, version markers or prior notes.
