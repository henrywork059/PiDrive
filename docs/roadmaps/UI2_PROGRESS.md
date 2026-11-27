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
