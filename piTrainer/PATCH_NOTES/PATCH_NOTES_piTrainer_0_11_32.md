# piTrainer 0.11.32 — Consolidated R35 desktop accessibility

## Verified baseline
Exact parent 20be5ad4446d8350726abd8645f09a0a0a3b5fed, Linux 45785643038 4/4 and Windows 45785642998 1/1, 36/36 Chromium, PiSD Node 27/27 and standard 63/63, PiServer Node 33/33, Windows Qt 15/15, manifests 7/7 and packages 11/11, forward dry runs 5/5/8. Actual artifacts 15100736466 and 15099279255 inspected in preceding review. Reviewed real launcher, shared widgets, canonical R35 and notes 0.11.31/30/29/28; next version absent on main, integration and matching branches.

## Changes
- piTrainer/ui/styles.py: retain semantic green palette, dark text on bright green primary/recommended/banner actions and saved/preprocessing done labels (8.27:1 default, 9.80:1 hover), white on dark green pressed (5.02:1), including highlighted pressed states; visible task-result focus border.
- piTrainer/ui/layout_widgets.py: restore disclosure header focus only if collapsing focused descendant; preserve unrelated focus and existing expansion state.
- piTrainer/panels/common/log_panel.py: contextual accessible name/description, strong focus and native Tab exit from read-only text.
- piTrainer/panels/common/task_progress_panel.py: named progress and synchronized current-step description across pending and terminal states; keyboard-selectable result/output paths. Actual task execution semantics unchanged.
- tests/test_shared_accessibility_r35.py: three native Qt regression cases for contrast across densities, disclosure focus continuity, log Tab and progress/result keyboard access. piTrainer/version.py: version markers.
- Shared Linux and Windows CI add syntax gates and new regression coverage.

## Verification and limits
Full changed Python files compiled locally with candidate Git blob hash matching; numeric contrast checked locally. Combined candidate browser/native Qt/package gate pending. No local Chromium or native Qt execution. No config, task, data, training, export, layout persistence, drive/motor, STOP, authorization or command lease changes. R35 partial; broader contrast/custom themes, screen readers, native touch/hardware/owner acceptance remain. No merge, stable promotion, deployment or Batch 6 advancement.

## Revision B — consolidated data-review continuation

- Actual Data selection now feeds a bounded read-only bulk-edit preview (two representative source session/frame identities, exact selected count, current and proposed steering/throttle, unknown labels retained). Slider/spin updates refresh the preview without mutation. Count-only resets clear stale identities. Existing overwrite checkbox, fresh selection lookup, explicit final confirmation, one-field writes and source identity rules remain unchanged.
- Files: piTrainer/panels/data/bulk_edit_panel.py, piTrainer/pages/data_page_filter_edit.py, tests/test_review_context_ux61.py. Existing comparison and contextual F1 help preserved; no shortcut, saved setting or layout-persistence changes. New native test covers duplicate frame IDs in separate sessions, missing labels, live values, clearing, no writes and unchanged confirmation gate. Native execution pending; no acceptance claimed.
- Forward from 50813d30b675062808fcf988a29536b40f8f4484; notes 0.11.32/31/30/29 reviewed in this cycle. No version allocation, stable promotion or deployment.


## Revision C — contextual shortcut discoverability and Windows review coverage

Last fully green baseline 2a36fe323f246d7264f70dc47ff1cf058c182133, Linux 45867333772 and Windows 45867334531. Linux review-context suite 6/6, native validation-to-data 5/5 on both, latest four notes 0.11.32/31/30/29 reviewed. Windows previously did not execute review-context suite.

- UX65: add a named secondary Shortcuts (F1) button in the existing status bar, using the same current-page help handler as F1. Preserve current mappings, tab order, layout and playback.
- UX61/UX63/UX65: register existing review-context suite on native Windows. Extend it with a real Qt harness using production shortcut bindings and read-only callback stubs: text-entry Space, Help button, F1, correct context and no mutations.
- Files: main_window.py, tests/test_review_context_ux61.py, Windows workflow. No data or persistent settings changes; no local Qt execution available, exact candidate syntax/native/packaging acceptance pending. No version allocation, merge or stable promotion.

## Revision D — software acceptance evidence (no trainer runtime change)
Exact verified baseline 5751280f107fb84c87bf0c113902ad49dc323dcd, Linux 45869069010 and Windows 45869069132 passed all five jobs. Actual PiSD artifact 15141562339 SHA-256 5096c95d417f67b914ca74acf139c2e7768a122f7d199dd4d4b703d69481655d and PiServer artifact 15141866729 SHA-256 f30aa64d7b204bf9e1a985b7a241b2040a6c7ca686e3c37a78982e5e6c440140 independently matched; all 78 cases zero errors. Forward packages 11/8/11 files passed.
Linux and Windows native review-context 7/7, existing validation-to-data 5/5 both, splitter/accessibility suites passed. Latest four notes reviewed. UX61, UX63 and UX65 software implementation accepted: stable source identity, read-only bulk preview, confirmation/cancel scope, same-frame comparison, contextual F1 and help button, text entry retained. Owner desktop visual and actual training/physical checks separate.

## Revision E — native acceptance continuity
Exact verified baseline c896700c068f1d9be14c84300c1035037cdd4a3f, Linux 45869995144 4/4 and Windows 45869995084 1/1. Independently matched actual artifact SHA-256: PiSD 15142042478 0b1431c45e418713b078dd0e46acd87056f8497da6585168cc30d3d0aa6baf56; PiServer 15142681656 9533e6a19e1868805e1bf5afa0b701f5d775c110ed8c9f77539b86f3cb03b91c. All 78 matrix cases exact revision, zero errors. Selected actual screenshots reviewed. Forward-package dry runs 14/10/11 changed files passed.
Review-context 7/7 and validation-to-data 5/5 on Linux and Windows, all other registered native tests passed. No trainer runtime or version change. Owner visual and physical acceptance separate.

## Revision F — integrated regression acceptance continuity
Exact green baseline 35be24a8ff55adbd50545542d2b2c3130cf814f9: Linux [45914883482](https://github.com/henrywork059/PiDrive/actions/runs/45914883482) 4/4 and Windows [45914883473](https://github.com/henrywork059/PiDrive/actions/runs/45914883473) 1/1. Independently matched actual artifacts PiSD 15161413659 SHA-256 3f90798edda903730ec9c5754cd516ff0f0ac79b088c318ff2ec9bf9b48d84a7 and PiServer 15161513250 SHA-256 e0c2db2bd3adae6d48cecd0528c112984900f678f6acfd1400dc82a3f8f43ff3. Six matrices exact revision, 78/78 zero case/page errors; 8/8 Manual/AI recording journeys including all seven checkpoints, exactly four recording POST requests per journey, duplicate/stale guard and actual handler tests passed. PiSD R36 17/17, PiServer R36 14/14 and R35 34/34; all 16 stacked STOP target dimensions 44px high. Windows native Qt eight suites passed (40 tests total); Linux trainer passed. Forward dry runs PiSD/PiServer/piTrainer 15/10/11 changed files passed. Selected actual screenshots reviewed.
R50 automated regression implementation verified, including native validation identity, splitter and focus tests. No trainer runtime/version change in this milestone. Owner visual approval and physical/assistive-technology acceptance separate.

## Revision G — exact integrated native acceptance checkpoint
Exact verified source ba2420536b733659c6cb4796490cdb38f8d31914, Linux [45915971367](https://github.com/henrywork059/PiDrive/actions/runs/45915971367) 4/4 and Windows [45915971393](https://github.com/henrywork059/PiDrive/actions/runs/45915971393) 1/1. Independently verified actual archives PiSD 15161709968 SHA-256 dcdd9d6261d15e90647071e05f21d17e6b8868a7b8b27c4fe9106920d7eea2f3 and PiServer 15162386493 SHA-256 9d3a3230a2a0e3442a29d8a6c028c09003ed1fdc562e7e9ab4370a951b0e683c. All six matrices, 78/78 cases, 8/8 recording journeys, no case/page errors. 256/256 actual width and height measurements >=44px (PiSD STOP 96, recording 48, dialogs 48; PiServer STOP 16, dialogs 48). Node PiSD responsive 18/18, PiServer responsive 15/15, accessibility 34/34; Windows native 40 tests, Linux trainer passed. Forward dry runs 15/10/11 changed files passed.
40 Windows native tests across eight suites; Linux trainer green. Existing trainer focus, selected validation identity, keyboard, splitter and non-color status contracts preserved. No native desktop screenshot artifact was produced by this workflow, so do not infer visual owner acceptance. No trainer runtime, config or version change.
