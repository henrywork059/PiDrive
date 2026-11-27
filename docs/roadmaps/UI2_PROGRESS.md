# UI/UX Improvement 2 — progress

2026-11-27. Original roadmap and the historical 56/56 completion accounting remain unchanged.

## Baseline inspection
- Main: 14c57c990ff0f9bae2003e4e8aa552d17a4227c7; previous Linux gate 45986688308 4/4.
- Performance 1 (#88): 04c62e457060270a6f3398a703de0b9b393162fa; Linux 46014075774, camera 46014075787, Windows 46014075899 and strict 46014075875 all passed. Numerical goals and owner transition are separate from workflow success.
- Performance 2 (#89): ba05d2acfa537acefd031dde3f1b79977f27652d; Linux 46026465707, Windows 46026465710, camera 46026467453 and strict 46026465612 all passed as of latest inspection.
- Emulator (#90): original 42674e49c94f86b73df06e6727a365edd7be5e16 Linux 46025487935 failed PiSD configuration recovery and native browser speed readback; Windows 46025488000 passed. Corrected separate emulator branch at d59c12da175c988a826e581ee83290040d478b52 restores the normal runtime settings path, adds workspace isolation test, and records revision B in its existing patch note. Exact corrected Linux 46027606067 and Windows 46027606187 were in progress when inspected. Do not claim closure yet.
- Original plan #91 at dece044a47c2b1261cad37063b9e7cd5e965ec60 passed Linux 46026490291 and Windows 46026490416.

## New development
| Requirement | Status | Evidence / remaining |
| --- | --- | --- |
| UI2-01 | Partial | Live branch and CI inventory; current code and notes checked. Full route/task timings and actual capture review pending. |
| UI2-02 | Proposed | Component token inventory and measured refinements pending. |
| UI2-03 | Partial | Native trainer readiness accessible names implemented; other feedback surfaces not changed. |
| UI2-04–08 | Proposed | Driving UI work awaits reconciled runtime baseline and measured findings. |
| UI2-09 | Partial | Native tab readiness semantics, unchanged labels and navigation. |
| UI2-10–12 | Proposed | Data, training, export and responsive audit/implementation pending. |
| UI2-13 | Partial, blocked on CI | Emulator path fix committed separately; exact corrected tests, simulator journeys and integration authorization pending. |
| UI2-14 | Partial | New Linux/Windows matched native Qt visual capture and navigation workflow; exact CI and artifact review pending. |
| UI2-15 | Proposed | Release qualification, reconciliation and owner acceptance pending. |

No complete UI2 item claimed: 0/15 complete, 5 partial, 10 proposed. Existing approved 105 web PNGs remain the reference, not replaced with candidate screenshots. Native before/after capture job added; no screenshot obtained or inspected in this session yet.

## Reference decisions
- Fluent 2 tabs and accessibility: https://fluent2.microsoft.design/components/web/react/core/tablist/usage and https://fluent2.microsoft.design/accessibility — visible text retained; state explicit in native tab accessibility API, no web framework.
- Qt 6.8 QTabBar API: https://doc.qt.io/qtforpython-6.8/PySide6/QtWidgets/QTabBar.html — native setAccessibleTabName, no new dependency.
- Carbon notifications: https://www.carbondesignsystem.com/building-blocks/core/patterns/notifications — prefer local, nondisruptive feedback for command results. No feedback redesign implemented yet.
- Component Gallery: https://component.gallery/components/accordion/ and https://component.gallery/components/button-group/ — progressive disclosure and consistent action grouping, to audit against existing controls.
- WCAG 2.2: https://www.w3.org/TR/WCAG22/ — focus visibility, names and target size; retain project-specific stricter STOP target and responsive gates.
- Remaining research and matched task measurements are still required.

## Next gate
Verify exact current PR91 CI and native screenshot artifacts, correct failures before continuing. Inspect corrected emulator CI; reconcile overlapping PiSD versions and code with #88/#89 without merging absent owner authorization. Native Qt is not installed locally and direct git network checkout is unavailable in the execution environment; GitHub connector used for current files, branch commits and CI inspection. No local full UI, hardware, actual screenshot or manual assistive-technology tests claimed. No version increment, tag, merge or stable promotion.

## Concurrent main reconciliation

PR #91 (plan only), #88 and #89 were merged externally during this session. Current main observed at 77b3fe8d6a76200caa7f96149c7d7c4bc66cb396 (PiSD 0.11.46, PiServer 0.4.55, piTrainer 0.11.34). The five independent UI2 changes were forward-ported to a new branch from that exact main, checking the unchanged trainer source blob and latest four notes. Native before capture uses this newer main. Emulator independently reconciled to 0.11.47 at 6bed7727d3a4e83c76ed207543f680ccb4b8dbae; Linux 46027914565 queued, Windows 46027914728 in progress at inspection. Confirm its final CI before integration. No merge performed by this task.

## 2026-11-27 — operator status foundation

- PR #92 exact 9e0fbaa Linux 46028062905: three component jobs passed; package gate failed first-parent baseline for PiServer. Native visual 46028063043: Linux/Windows both passed. Emulator 6bed7727 Linux 46027914565: three component jobs passed; historical 0.11.46 note mismatch in package gate; Windows 46027914728 passed. PR #90 merged externally; main b57f02c920cd4d65fe584b8eb4dcf9bd74e6ae71 restores exact 0.11.46 note (same blob as 77b3fe8d). No retroactive claim of green CI.
- Downloaded actual native artifacts 15213935053 (Linux SHA-256 94952973521952f042ccec9ecfc007e0c17939d56d06ca855811a038a0233d23) and 15213735418 (Windows e499eb60a695f8b135eb5d0314572cf014d6763b74f35a1d7683a74ce6be6336). Both archives verified against GitHub metadata. All 48 PNG hashes and dimensions matched four manifests, before 77b3fe8d and after 9e0fbaa, six pages x two sizes per revision/platform. Accessible names reflect exact readiness details in all three fixture states; baseline explicit names were empty. All four before/after montages inspected. Linux layouts broadly consistent; 0/12 PNG pairs byte-identical (rendering/paths differ). Windows 7/12 identical but missing-glyph boxes in both revisions render almost all UI text unreadable; reject as visual acceptance evidence despite green test. Correct platform/font preflight separately. No manual screen-reader, physical or owner acceptance.
- Current operator branch from exact main, provisional PiSD 0.11.48 and PiServer 0.4.56. Runtime labels distinguish emulator, fallback, hardware adapter, simulation and unconfirmed. Preserve offline state across local controls, align displayed camera/model/adapter telemetry; dashboard cold/offline no longer claims verified E-STOP or stale server metrics. Shared semantic readiness foreground tokens preserve existing palette. Guard unchanged text/tone writes. 36/36 readiness cases via actual V8 helper/harness, PiServer actual extracted offline function test passed, modified JS syntax parsed. New native browser/package CI pending. No new polling, actuator authority or persisted settings.
- Ported identical-component package-source guard from pending #93: unchanged trainer may use exact qualified ba05d2a only when full ancestor and entire component tree identical; changed runtime candidates use new one-step immutable baseline and original anti-rollback/package checks. No historical notes rewritten. Trainer 0.11.35 reserved in #93, not allocated here. Keep prior trainer accessibility source on PR #92 until forward reconciliation; new trainer milestone should stack after #93 or use its accepted integration, never overwrite its performance changes.
- UI2-01/02/03/04/05/07/08/09/13/14 partially addressed; UI2-06/10/11/12/15 proposed. 0/15 fully accepted; 10 partial, 5 proposed. No completion of M0–M4 claimed. Old 56/56 and approved web screenshot baseline unchanged. Remaining: exact new browser CI, actual web screenshot review and matched task timings; full workflow changes, trainer visible readiness and valid Windows capture, emulator fault journeys, responsive/performance and owner qualification. No merge or stable promotion.

## 2026-11-28 — combined operator and trainer workflow continuation
- Verified main b57f02c920cd4d65fe584b8eb4dcf9bd74e6ae71; #93 0f28889459796c6672b0b830c095205c83579e11; #94 starting 8114fed6153c30aa99da764d7e6c55f635de7afb; #95 starting 7151a8a2919430dd3281cc2a838d254a581c4cfe. #94 starting Linux 46030503707 and Windows 46030503635 passed. #95 Linux 46030742183 failed only the reported three materialization cases in the trainer regression job (plus dependent interpreter comparison); the exact corrected #93 Linux 46031258094 and Windows 46031258108 passed; workload 46031258088 and strict 46031258455 were pending at inspection.
- Independently downloaded and checked archive integrity and actual screenshots: 15214491363 SHA-256 0dd223092c731ee91b99d14be6e775da84d69792a429c917f2531c6053040366; 15214825501 dcaf1b19023e65e700bd717fdb308280e87b365997567a62d392117d82a16c0d; 15214895480 a79c41d6f4c6052a49a6181a7b95f38596bf2105550fc1ead9b497c47c7e2cee; 15214905546 bd69950cdbc8b67a52a70ef027d410f2fdd2fbe2760b2baeeb7a7f53863b8f28. 109 web PNGs; 48 native PNGs, all native manifest hashes and dimensions matched. Native before 4d2f66a, after 7151a8a2. Windows Segoe UI glyph probe and representative images readable, but requested 1024x768 and 1440x900 captured at 1024x749 and 1028x749. Reject wide-layout qualification. Empty trainer workspace is not end-to-end workflow evidence. Original 105 approved web PNGs unchanged.
- #95 e7a5cbb96947bad5497551c4fe4a5583ee7a1320 forward-ports all 15 concurrent performance paths (14 exact blobs and combined workflow conditions), preserves column-order/global inference contracts, adds visible prerequisite details and contextual navigation without automatic execution, and captures navigation timing/logical geometry. Extracted fixed materializer passed 300 deterministic randomized comparisons plus three empty-column cases on pandas 2.2.3. New exact Linux 46032023140, Windows 46032023170, visuals 46032023012 pending at observation. No full native local run. Stacked #95 still needs final reconciliation with main and #94.
- #94 revision B adds compact PiSD workflow anchors and page-filtered PiServer stacked-panel navigation, with browser checks for target geometry, one interaction and no mutation. No new runtime commands, polling, settings or layout migration. Desktop navigation hidden; actual new candidate geometry and timings await exact CI.
- UI2-06 and UI2-12 now additionally partial (navigation and evidence instrumentation only). 0/15 accepted, 12 partial, 3 proposed (10/11/15). Existing 56/56 accounting unchanged. M1–M4 not closed: actual matched timing, populated trainer workflow, broad cockpit layout improvements, emulator fault journeys, visual and strict performance qualification, physical safety and owner acceptance remain open. No new versions, merge or stable promotion.


## Consolidation for owner-requested merge
- Main f5e58cf has qualified PiSD 0.11.48 iframe repair (#96); retain it. Performance #93 exact 0f288894 passed all four workflows. #97 supersedes #95 with identical trainer UI and harness code, corrected package ancestry; #92 readiness is retained in #97 and its checkpoint note is included. Integrate on a separate branch preserving original source revisions. UI2 PiSD renumbered 0.11.49, PiServer 0.4.56, trainer 0.11.36 after qualified 0.11.35 source. All combined CI and visual acceptance pending; no completion or stable promotion claimed.


## Combined qualification revision
- Owner additionally requested promotion to the next version. Keep merge and stable/full-baseline promotion distinct: repository stabilization policy requires separate physical P0 acceptance before stable promotion. Next stable series would require explicit version-family migration in packaging and matching baseline records; do not mark physical checks as passed or disable gates. Current candidate versions remain 0.11.49 / 0.4.56 / 0.11.36 until the combined revision qualifies.
- Linux 46033174578 failed PiServer AX inventories on generic unnamed workflow jump targets; all other component/package jobs passed. Correct the eight target headings without changing navigation or loosening checks. Emulator 46033174814, Windows 46033174643 and trainer visual 46033174638 passed; long performance workflows still pending at inspection. Re-run full combined CI; visual artifacts and physical validation remain separate.
