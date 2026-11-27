# PiDrive — UI/UX Improvement 2: workflow and design-system roadmap

Date: 2026-11-27  
Status: **Proposed, planning only; implementation and visual approval pending.**  
Planning baseline: main `14c57c990ff0f9bae2003e4e8aa552d17a4227c7`.  
Scope: PiSD, PiServer, piTrainer; conditional PiSD Emulator integration after its separate acceptance.  
Source: owner-provided “UI/UX design resource collection” (2026-11-27).

## 1. Purpose and baseline

Improve the real operator and training experience: faster task completion, less cognitive load, coherent component behavior, clearer feedback and responsive/accessibility quality. Favor functional engineering applications, not promotional dashboards. Avoid a redesign for its own sake.

This is a **new follow-on track**, not a reopening or renumbering of the original [UX54–UX75 plan](PiDrive_UI_UX_Improvement_Plan.md). The [completed roadmap](README.md) records 56/56 active software proposals and 9/9 batches. Preserve that accounting. The [release-candidate handover](RELEASE_CANDIDATE_HANDOVER.md) records main candidates PiSD 0.11.45, PiServer 0.4.53, piTrainer 0.11.32; these are not new stable versions. Separate native visual, assistive-technology, physical touch, hardware and deployment acceptance remains open.

The owner-approved web visual reference is exactly source `ba2420536b733659c6cb4796490cdb38f8d31914`, 105 PNGs (83 PiSD, 22 PiServer), as documented in [ui_baseline_review.md](../ui_baseline_review.md). Retain its original archive digests and manifest; do not substitute newly generated goldens. Any intentional visible differences require before/after evidence and separate owner approval.

Parallel work observed at planning time:
- [Performance Update 1, PR #88](https://github.com/henrywork059/PiDrive/pull/88), branch `update/performance-1-computation`, observed HEAD `04c62e457060270a6f3398a703de0b9b393162fa`.
- [PiSD Emulator E01](https://github.com/henrywork059/PiDrive/tree/codex/pisd-emulator-e01-20261127), observed HEAD `42674e49c94f86b73df06e6727a365edd7be5e16`, includes a separate `PiSD_Emulator/` control application and PiSD changes.
- Both pending branches touch PiSD 0.11.46; reconcile actual source, version and patch-note collisions before allocating a new candidate. Do not independently replay either older tree or merge without authorization. Do not alter the pending performance gate. Verify current HEADs and exact CI before starting implementation.
- Inactive PiBooter, CustomTrainer, CustomDrive and legacy piCar remain out of scope, retained unchanged.

Planning evidence: live main README, AGENTS.md, roadmap index, existing UI/UX plan, component READMEs and visual approval record were read; branch commit metadata inspected. No new screenshot review, running UI audit, library integration, benchmark or runtime/hardware test was performed for this document. Proposed opportunities are hypotheses, not confirmed new defects. Each requires code and rendered-state verification first.

## 2. Reference research and design decisions

Use the supplied resource collection to select patterns, not to mandate dependencies. At implementation time record reference URL, pattern, observed trade-offs, adapted design, existing alternative, affected workflow and acceptance test. Do not copy a product's visual identity or redistribute its reference assets. The resource descriptions below are drawn from the supplied collection; current library versions, licenses and compatibility have not been independently verified in this planning task.

| Resource | Apply to PiDrive |
| --- | --- |
| [The Component Gallery](https://component.gallery/) | Compare accordion, tabs, popover, dialog, table, toolbar and tree patterns; choose a tree only when actual hierarchical data warrants it. |
| [Mobbin](https://mobbin.com/), [Refero](https://refero.design/), [Page Flows](https://pageflows.com/) | Research complete workflows: start, select, operate, recover, save and return; desktop workspace compositions. |
| [SaaSFrame](https://www.saasframe.io/), [Dribbble](https://dribbble.com/) | Secondary visual inspiration; never treat mockups as proof of usability or working behavior. |
| [IBM Carbon](https://carbondesignsystem.com/), [GitHub Primer](https://primer.style/) | Technical status, data density, tables, diagnostics, progress and experiment comparisons. |
| [Fluent 2](https://fluent2.microsoft.design/), [Apple HIG](https://developer.apple.com/design/human-interface-guidelines/), [Material 3](https://m3.material.io/) | Workspace, toolbar, navigation, focus, responsive behavior and platform conventions. |
| [Ant Design](https://ant.design/), [Atlassian](https://atlassian.design/) | Settings, management workflows, feedback, error recovery and complex forms. |
| [shadcn/ui](https://ui.shadcn.com/), [Radix UI](https://www.radix-ui.com/), [React Aria](https://react-spectrum.adobe.com/react-aria/) | Reference behavior for accessible primitives and customizable controls, not a framework migration. |
| [Mantine](https://mantine.dev/), [21st.dev](https://21st.dev/), [Tremor](https://www.tremor.so/), [React Flow](https://reactflow.dev/) | Optional research only if an actual existing feature warrants a component. No new node editor, React bundle or chart dependency by default. |
| [Lucide](https://lucide.dev/), [Storybook](https://storybook.js.org/) | Evaluate consistent locally hosted icons and isolated component test patterns; prefer existing assets and test harnesses. |
| [Radix Colors](https://www.radix-ui.com/colors), [Realtime Colors](https://www.realtimecolors.com/), [Happy Hues](https://www.happyhues.co/), [Type Scale](https://typescale.com/), [Figma Community](https://www.figma.com/community) | Explore semantic token roles, contrast and hierarchy in prototypes; preserve accepted palettes and customization until explicitly approved. |
| [Nielsen Norman Group](https://www.nngroup.com/articles/), [Laws of UX](https://lawsofux.com/), [Refactoring UI](https://www.refactoringui.com/), [Growth.Design](https://growth.design/case-studies), [UI Patterns](https://ui-patterns.com/) | Task-first information architecture, recognition, recovery, progressive disclosure, fewer competing actions. |
| [Checklist Design](https://www.checklist.design/), [WCAG 2.2 quick reference](https://www.w3.org/WAI/WCAG22/quickref/), [WebAIM contrast checker](https://webaim.org/resources/contrastchecker/) | Component states and accessible interaction validation. |

Design direction: Carbon's information organization + Fluent's workspace composition + the customization flexibility demonstrated by shadcn/ui. PiSD emphasizes Fluent and Radix interaction patterns; PiServer emphasizes Carbon and Ant Design; piTrainer emphasizes Primer, Refero and Fluent desktop conventions. The existing Python/web and native Qt stacks remain. No new framework, CDN, external font request, analytics service, theme reset or library is approved by this plan. For any justified dependency, evaluate license, maintenance, security, distribution/offline behavior, compatibility, cold load, bundle and runtime cost, plus a no-dependency alternative; obtain approval for material architectural changes.

## 3. Shared interface contract (component-local implementation)

- Establish semantic token inventory for typography, spacing, density, surfaces, border, focus, icon size, primary/secondary/danger and state roles. Use existing component-local styles/QSS/theme systems; document shared semantic mappings, not cross-component runtime imports. Proposed scale starts from existing accepted values, not a forced rebrand. Preserve user themes and settings; verify defaults and supported custom variants separately.
- Maintain clear alignment, grouping and hierarchy; one primary action per task group, short labels, few decorative containers, whitespace instead of redundant borders. Keep context and safety information visible. Advanced disclosures retain access, values and focus; closing a panel must not reset config or change real device state.
- Define reusable behavior for buttons, inputs with units, tabs, toolbars, dialogs, disclosures, tables, notifications, tooltips, loading/empty/error/stale/disabled/selected/success states. Prefer text plus icon/shape, never color alone; no tooltip-only essential label. Distinguish request pending from backend-confirmed success; provide recoverable errors and accurate disabled reasons. No fake progress or telemetry.
- Keyboard order, focus return, visible focus, accessible names and roles, reduced motion, forced-colors where supported, keyboard/non-drag alternatives, no hover-only essential control. Target WCAG 2.2 AA applicable web criteria (normal text 4.5:1; large text and relevant non-text UI 3:1); preserve the existing measured >=44 CSS px critical/touch target gate rather than relaxing it to the WCAG minimum. Native Qt accessibility needs platform testing.
- Do not add animation, network requests or polling merely for polish. Use local assets, bounded rendering and existing lifecycle behavior; do not obscure or delay safety controls. Layout state is distinct from runtime state; no migration may silently overwrite settings or saved user layouts.

## 4. Proposed implementation backlog

All UI2 IDs below are new, **proposed**, not yet implemented or verified. P0 = acceptance/safety prerequisite; P1 = primary workflow value; P2 = refinement after evidence. Existing features must be inventoried before editing; if already satisfied, record exact evidence rather than duplicate implementation.

| ID | Priority | Scope | Work and observable done condition |
| --- | --- | --- | --- |
| UI2-01 | P0 | All | Capture exact current routes/pages, screenshots, controls, runtime actions and real task timings at accepted baseline; catalogue actual usability friction with reference patterns and evidence. Pin originals, versions, configuration fixtures, viewport, hardware/sim mode. |
| UI2-02 | P1 | All | Inventory component tokens and eliminate demonstrated duplication incrementally. Compare dark/light or supported custom themes; no default palette or saved theme regression; contrast and visual diffs reviewed. |
| UI2-03 | P1 | All | Standardize action hierarchy and state feedback within each component. Check pending, success, rejection, stale data, disabled reasons, destructive confirmation and recovery using actual responses; STOP never confirmation-gated. |
| UI2-04 | P1 | PiSD | Refine Manual Drive cockpit: status first, dominant camera, compact control/action strip, unmistakable actual mode, accessible persistent STOP. Measure preview usable area and reachability without changing steering, throttle, input bindings or motor logic. |
| UI2-05 | P1 | PiSD | Refine AI Mode workflow from model selection and readiness to preview/run/stop. Show actual control source, model, camera freshness and fault state; keep existing correction modes and single motor safety confirmation. Verify rejected starts never appear successful. |
| UI2-06 | P1 | PiSD | Unify recording/snapshot feedback and session browsing where inconsistent. Keep confirmed filename/count/status, recoverable failures and labels compatible with piTrainer. Calibration/settings grouped with units and explicit apply/cancel/reset; confirm readback and restart persistence. |
| UI2-07 | P1 | PiServer | Refine default dock workspace: preview and essential run state prominent, telemetry tiered, clear primary vs layout vs destructive actions. Preserve all panels, resizing, custom presets, focus, tuning, save/reset and theme behavior; E-Stop always reachable. |
| UI2-08 | P1 | PiServer | Improve device/model/recording management and settings recovery using consistent tables, forms and feedback. Preserve auth/CSRF, validation, effective settings, model compatibility and redacted trace references; verify failed apply/save and restart. |
| UI2-09 | P1 | piTrainer | Refine existing six-stage workspace and page-local action placement; use compact prerequisites, stable tabs and contextual help, no extra Next step button. Preserve docking/floating, splitters, shortcuts and workflow state across navigation/restart. |
| UI2-10 | P1 | piTrainer | Data/preview workflow: compare labels/predictions on the same stable row, preserve playback below preview, filtering, selection, bulk-edit preview and deletion safeguards. Measure navigation/action count and frame consistency on real deterministic fixtures. |
| UI2-11 | P1 | piTrainer | Train/Validate/Export/Export Validation: align progress and error language, artifact identity/path visibility, metrics and experiment comparisons. Verify cancellation, failures, unique outputs, checksum/provenance linkage and real export; never imply a partial job succeeded. |
| UI2-12 | P2 | All | Improve demonstrated navigation or density issues at compact viewports, keyboard and larger text/scaling. Preserve semantics and use current responsive/layout mechanisms; no concealed STOP or horizontal clipping of essential controls. |
| UI2-13 | P0 | PiSD Emulator (conditional) | After E01 integration is approved, use the real PiSD HTML UI against the emulator for deterministic camera, motor input/output, disconnect, stale/fault, recording and stop scenarios. Keep emulator controls distinct from actual driving UI; explicit simulated state and no physical GPIO authority. Do not duplicate PiSD frontend or conflate simulation evidence with real hardware. |
| UI2-14 | P0 | All | Extend existing rendered browser and native Qt acceptance, capture actual before/after evidence for changed surfaces, audit usability and accessibility. Native desktop screenshot package and manual screen-reader/touch checks are separate gates. |
| UI2-15 | P0 | All | Consolidated release qualification, performance comparison, exact version/patch integrity, owner visual review and deployment safety evidence as applicable. No stable promotion or merge without separate authorization. |

### Component implementation anchors (verify again at execution)

The existing component README/roadmap identifies launchers `PiSD/PiSD.py`, `PiServer/server.py`, `piTrainer/main.py`. The historical plan identifies PiSD Manual Drive/AI Mode templates and CSS/JS under `PiSD/pisd/web/`, including `pisd_layout_system.css`; PiServer's index, styles, app and theme assets under `PiServer/piserver/web/`; and trainer page/panel/UI modules under `piTrainer/piTrainer/`. Treat these as starting points from the documented architecture, not a verified exhaustive current file inventory. Inspect the live tree, exact launch paths, current CSS order, handlers, settings and latest plus previous three component patch notes before modifying anything.

Keep PiSD status-before-preview, safety confirmation, global Space STOP and existing hidden-tab streaming behavior. Keep PiServer E-Stop, layout persistence, auth and service separation. Keep trainer green main-action / amber prerequisite semantics, stable row identity, export checks and no restored Next step UI. Preserve already accepted UI, layout, runtime and config behaviors; report intentional changes separately.

## 5. Milestone execution order

| Milestone | Work | Exit gate |
| --- | --- | --- |
| M0 — Baseline & research | UI2-01; establish UI2-14/15 acceptance harness and UI2-13 dependency status. | Exact current code/CI verified; original approved images retained; actual route, screen and task inventory, baseline metrics, selected reference patterns and prioritized findings. |
| M1 — Foundation | UI2-02/03, targeted state/a11y primitives across active components. | Existing workflow and visual baseline pass except documented candidate diffs; no new runtime dependency or safety regression. |
| M2 — Driving interfaces | UI2-04–08; integrate emulator test scenarios from UI2-13 only when authorized and compatible. | Manual/AI/PiServer journeys, simulated faults, confirmed runtime state, STOP/rearm tests and browser evidence. |
| M3 — Training workspace | UI2-09–11. | Native Qt interaction and screenshot matrix, real data→preprocess→train→validate→export→export validation workflow and negative cases, preserved saved layouts. |
| M4 — Responsive polish and acceptance | UI2-12/14/15; finish applicable UI2-13 integration. | Exact CI, visual review package, performance comparison, anti-rollback audit, unresolved physical/native gates clearly stated; owner acceptance requested. |

Combine related requirements into substantial milestones, not isolated cosmetic micro-patches. Group by dependencies and risks, not arbitrary version increments. Existing performance milestone takes precedence for conflicting files; M0 and independent planning can proceed without touching its branch. At implementation, choose the newest accepted base, reconcile pending emulator/performance changes, and obtain authorization for any integration or merge.

## 6. Validation and measurable outcomes

Use pre/post matched fixtures and report actual counts, distributions and failures. Proposed targets are acceptance criteria for future work, **not measured improvements or guarantees**. Confirm feasibility in M0; any relaxed gate requires explicit rationale and approval.

| Measure | Evidence / proposed acceptance |
| --- | --- |
| Functional preservation | Existing registered software regressions pass; all enabled controls in affected journeys remain reachable and perform the same intended action; no missing required workflows. Verify actual requests/responses and persisted data, not screenshots alone. |
| Workflow efficiency | Record action count and task completion time for opening/operating Manual and AI modes, camera/motor/model setup, recording/export and trainer review. No extra mandatory actions on core tasks; target >=10% fewer non-safety interactions for workflows where M0 demonstrates avoidable friction. Report unchanged tasks honestly; never remove required safety confirmations. |
| Layout | Keep prior 78-case web matrix, existing 105-image comparison and critical target coverage; add affected states rather than shrinking coverage. Include 390/768/1440 widths and existing landscape/short/large cases; no unintended overlap/clipping and actual critical targets >=44 px each dimension. Retain stricter existing geometry contracts. |
| Accessibility | Existing AX/name/focus tests pass; keyboard, Escape, focus return, reduced motion, contrast, non-color signals and supported forced-color states verified. Zero new critical/serious findings in scoped checks; manual native assistive-technology testing remains separate. |
| Performance | Compare matched cold/warm load, UI action response p50/p95, preview FPS, command latency, request count/bytes, CPU/RSS and trainer interaction latency where relevant. Preserve all stricter Performance Update 1 gates. Proposed UI p95 non-inferiority within 5% only with sufficient repeatability; if noisy, report uncertainty and retest. No increased hidden-tab streaming or unnecessary polling; no weakened safety timing. Physical Pi evidence separate. |
| Persistence/data | Existing config values, unknown keys, theme/layout and selection identities retained; save/apply/restart round-trip; no accidental overwrite or recording/model/manifest compatibility regression. |
| Safety | STOP immediately available; existing watchdog, latch, disconnect/tab visibility, command rejection, no auto-arm, camera fault, model-family and auth/CSRF contracts unchanged. Simulation cannot actuate physical outputs; physical acceptance performed separately under existing safe procedures. |
| Review evidence | Exact commit, CI links, screenshot manifests and hashes, fixture and environment description, before/after changed surfaces, workflow tests and unresolved cases. No new approved golden without explicit owner decision. |

For each milestone include representative happy, slow, disconnected, stale, no-data, missing-model, rejected-save, invalid-input and recovery states; test mouse, keyboard, safe touch and native desktop scaling. For web, use existing browser/fixture tooling first; for native trainer, use existing Qt tests plus actual Windows/Linux screenshots as applicable. Never count a mock response or screenshot as a physical motor or camera test. Existing physical, frozen EXE, deployment and native acceptance limits in the handover remain in force.

## 7. AI-agent implementation protocol

1. Read AGENTS.md, this plan, existing roadmap, current acceptance and relevant performance gates. Verify live main and pending branches, versions, actual entry points, current source and latest + preceding three patch notes.
2. Reproduce an actual problem or document a justified improvement with a named reference pattern; record the task and baseline. Propose component-local changes and explicitly identify any intentional visual difference.
3. Implement the smallest complete functional milestone; preserve local config, approved workflows, safety/runtime contracts and existing tests. No broad framework migration or inactive-component edits.
4. Run relevant unit, integration, browser/Qt and exact-revision CI; inspect actual rendered output and compare to pinned approved web baseline. Record negative cases, metrics and known limitations; do not weaken tests to obtain green status.
5. Review anti-rollback against latest accepted state and pending integration, reconcile version collisions, update component patch notes for actual patches, and produce changed-file-only packages only when requested under existing rules.
6. Report UI2 item status with evidence (proposed / in progress / scoped automated pass / owner accepted / physical or native gate pending). Keep a separate UI2 tracker when implementation begins; do not modify 56/56 historical accounting. Request owner review for intentional visual changes; do not merge, tag, deploy or promote stable without explicit authorization.

**Immediate next implementation task (not executed by adding this plan):** M0 baseline and research after checking the newest accepted runtime state and current performance/emulator branches. Establish the UI2 findings, approved-reference preservation and evidence matrix; then group high-value, independently safe changes for M1/M2. No application source, version markers, historical progress counts or approved baseline artifacts are changed by this planning document.
